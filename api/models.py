from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import random
import uuid

class NIMCRecord(models.Model):
    """
    Simulated NIMC database. Primary anti-fraud perimeter.
    Accessed via the NIMC API Integrator role.
    """
    nin = models.CharField(max_length=11, unique=True, verbose_name="NIN")
    full_name = models.CharField(max_length=150)
    state = models.CharField(max_length=100)
    lga = models.CharField(max_length=100, verbose_name="LGA")
    biometric_hash = models.TextField(help_text="Encrypted baseline for bimodal BVAS matching")

    def __str__(self):
        return f"{self.full_name} ({self.nin})"

    class Meta:
        verbose_name = "NIMC Record"
        verbose_name_plural = "NIMC Records"


class PollingUnit(models.Model):
    """
    Geographic edge-node for the electoral network.
    """
    id = models.CharField(max_length=50, primary_key=True) # e.g., 'PU-24-05-11'
    name = models.CharField(max_length=200)
    ward = models.CharField(max_length=100)
    lga = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    registered_voters_count = models.PositiveIntegerField(default=0)
    presiding_officer = models.ForeignKey(
        'ElectoralUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_pu_as_po', limit_choices_to={'role': 'po'}
    )
    collation_officer = models.ForeignKey(
        'ElectoralUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_pu_as_co', limit_choices_to={'role': 'co'}
    )

    def __str__(self):
        return f"{self.name} - {self.id}"

    def save(self, *args, **kwargs):
        if not self.id or self.id.strip() == "":
            while True:
                candidate = f"PU-{random.randint(100000, 999999)}"
                if not PollingUnit.objects.filter(id=candidate).exists():
                    self.id = candidate
                    break
        super().save(*args, **kwargs)


class ElectoralUser(AbstractUser):
    """
    Expanded User model serving the entire e-voting ecosystem.
    Replaces the basic 'Voter' to accommodate comprehensive RBAC.
    """
    ROLE_CHOICES = [
        ('prospective', 'Prospective Voter'),
        ('voter', 'Registered Voter'),
        # --- INEC HQ Roles ---
        ('commissioner', 'INEC Electoral Commissioner'),
        ('secretary', 'INEC Secretary'),
        # --- Field Roles ---
        ('po', 'Presiding Officer (PO)'),
        ('apo', 'Assistant Presiding Officer (APO)'),
        ('spo', 'Supervisory Presiding Officer (SPO)'),
        ('co', 'Collation Officer (CO)'),
        ('ro', 'Returning Officer (RO)'),
        ('agent', 'Polling / Party Agent'),
        ('media', 'Accredited Media / Journalist'),
        ('observer', 'Election Observer'),
        ('auditor', 'Cybersecurity Auditor'),
    ]

    username = models.CharField(max_length=11, unique=True, verbose_name="NIN")
    staff_number = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Staff Number")
    vnin = models.CharField(max_length=16, blank=True, null=True, verbose_name="Virtual NIN")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='prospective')
    
    # Demographics & Placement
    full_name = models.CharField(max_length=150)
    state = models.CharField(max_length=100)
    lga = models.CharField(max_length=100, verbose_name="LGA")
    assigned_polling_unit = models.ForeignKey(PollingUnit, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Security & Authentication State
    is_verified = models.BooleanField(default=False)
    passed_bimodal_auth = models.BooleanField(default=False, help_text="Facial/Fingerprint verified at BVAS")

    voter_id = models.CharField(max_length=19, unique=True, blank=True, 
        null=True, verbose_name="Voter Identification Number (VIN)")
    
    date_of_birth = models.DateField(blank=True, null=True)
    
    # Accessibility
    needs_assistance = models.BooleanField(default=False, help_text="Flags profile as Assisted Voter")
    ui_configuration = models.JSONField(default=dict, help_text="Stores TTS or high-contrast preferences")
    language = models.CharField(max_length=50, default='English', help_text="Preferred interface/voice language")

    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'full_name', 'state', 'lga']

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        if self.role not in ['prospective', 'voter'] and (not self.staff_number or self.staff_number.strip() == ""):
            from .utils import generate_staff_id
            self.staff_number = generate_staff_id(self.role, self.state)
        super().save(*args, **kwargs)



class OTPVerification(models.Model):
    """
    Multi-Factor Authentication (MFA) gateway tokens.
    """
    PURPOSE_CHOICES = [
        ('signup', 'Signup Verification'),
        ('reset', 'Password Reset'),
        ('ballot_auth', 'Ballot Cast Authorization'),
    ]

    user = models.ForeignKey(ElectoralUser, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=15, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    @classmethod
    def generate_otp(cls, user, purpose):
        # Generate 6-digit numeric OTP
        code = "".join(random.choice("0123456789") for _ in range(6))
        
        # Deactivate any previous unused OTPs for this user/purpose
        cls.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)
        
        # Create and return new OTP
        return cls.objects.create(
            user=user,
            code=code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=10)
        )

    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at


class Election(models.Model):
    """
    Represents a ballot or election, aggregating final datasets.
    Lifecycle: drafted → upcoming → active → collation → closed
    """
    STATUS_CHOICES = [
        ('drafted', 'Drafted (Internal)'),
        ('upcoming', 'Upcoming (Published)'),
        ('active', 'Active (Polls Open)'),
        ('collation', 'Collation Phase'),
        ('closed', 'Closed (Final Published)'),
    ]

    ELECTION_TYPE_CHOICES = [
        ('presidential', 'Presidential'),
        ('gubernatorial', 'Gubernatorial'),
        ('senatorial', 'Senatorial'),
        ('house_reps', 'House of Representatives'),
        ('state_assembly', 'State House of Assembly'),
        ('council', 'Local Government / Council'),
    ]

    id = models.CharField(max_length=100, primary_key=True)
    title = models.CharField(max_length=200)
    election_type = models.CharField(
        max_length=30, choices=ELECTION_TYPE_CHOICES,
        default='presidential', verbose_name="Election Type"
    )
    description = models.TextField(
        blank=True,
        help_text="Official INEC description of this election/ballot"
    )
    date = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='drafted')
    start_time = models.TimeField(default='08:30:00')  # 8:30 AM
    end_time = models.TimeField(default='14:30:00')
    eligible_states = models.JSONField(
        default=list,
        help_text="List of state names eligible to participate. Empty = nationwide."
    )
    created_by = models.ForeignKey(
        'ElectoralUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_elections'
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    blockchain_contract_address = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def can_accept_votes(self):
        return self.status == 'active'


class Candidate(models.Model):
    """
    Contenders interacting via the INEC Candidate Nomination Portal (ICNP).
    """
    id = models.CharField(max_length=100, primary_key=True)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name="candidates")
    name = models.CharField(max_length=150)
    party = models.CharField(max_length=150)
    party_abbr = models.CharField(max_length=20)
    color = models.CharField(max_length=10, default="#1565c0")
    manifesto = models.TextField()
    running_mate = models.CharField(max_length=150, blank=True, null=True)
    votes_count = models.PositiveIntegerField(default=0)
    legal_affidavit_url = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.party_abbr})"


class ResultSheet(models.Model):
    """
    Digital equivalent of Form EC8A. Uploaded directly to IReV by the PO.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    polling_unit = models.ForeignKey(PollingUnit, on_delete=models.SET_NULL, null=True, blank=True)
    presiding_officer = models.ForeignKey(ElectoralUser, on_delete=models.RESTRICT, related_name="submitted_results")
    
    scanned_form_url = models.URLField(help_text="Link to IReV portal document")
    accredited_voters = models.PositiveIntegerField()
    total_votes_cast = models.PositiveIntegerField()
    
    # Cryptographic & Physical countersignatures
    po_digital_signature = models.CharField(max_length=256)
    is_countersigned_by_agents = models.BooleanField(default=False)
    
    # Mathematical audit
    flagged_for_overvoting = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Enforce Section 64 mathematical check
        if self.total_votes_cast > self.accredited_voters:
            self.flagged_for_overvoting = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Form EC8A - {self.polling_unit.id} ({self.election.id})"


class DisputeLog(models.Model):
    """
    Allows Party Agents/Observers to flag impersonation or technical faults.
    """
    polling_unit = models.ForeignKey(PollingUnit, on_delete=models.CASCADE)
    raised_by = models.ForeignKey(ElectoralUser, on_delete=models.CASCADE)
    description = models.TextField()
    is_resolved = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)


class ElectionParticipation(models.Model):
    """
    Enforces the 'one person, one vote' constraint. 
    Strictly bifurcates the voter's identity from their electoral selection.
    """
    voter = models.ForeignKey(ElectoralUser, on_delete=models.CASCADE, related_name="participations")
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name="voter_records")
    voted_at = models.DateTimeField(auto_now_add=True)
    cryptographic_receipt = models.CharField(max_length=256, blank=True, help_text="Hash proving interaction with smart contract")

    class Meta:
        unique_together = ('voter', 'election')

    def __str__(self):
        return f"{self.voter.username} voted in {self.election.title}"


class AuditLog(models.Model):
    """
    Tracks CRUD operations performed in the system.
    """
    user = models.ForeignKey(ElectoralUser, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10)  # 'CREATE', 'UPDATE', 'DELETE'
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    def __str__(self):
        actor = self.user.username if self.user else "System"
        return f"{actor} performed {self.action} on {self.model_name} (ID: {self.object_id})"


class StaffInvitation(models.Model):
    """
    Secure token-based invitation system for pre-provisioning electoral officials.
    Replaces the need for a single super-admin to manually create accounts.
    ICT Officers generate invites; officials activate via email link + NIN biometric challenge.
    """
    ROLE_CHOICES = [
        ('commissioner', 'INEC Electoral Commissioner'),
        ('secretary', 'INEC Secretary'),
        ('po', 'Presiding Officer (PO)'),
        ('apo', 'Assistant Presiding Officer (APO)'),
        ('spo', 'Supervisory Presiding Officer (SPO)'),
        ('co', 'Collation Officer (CO)'),
        ('ro', 'Returning Officer (RO)'),
        ('auditor', 'Cybersecurity Auditor'),
    ]

    token = models.CharField(max_length=64, unique=True)
    invited_email = models.EmailField()
    staff_number = models.CharField(max_length=50, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    assigned_polling_unit = models.ForeignKey(PollingUnit, on_delete=models.SET_NULL, null=True, blank=True)
    invited_by = models.ForeignKey(
        ElectoralUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sent_invitations'
    )
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    @classmethod
    def create_invitation(cls, email, staff_number, role, invited_by, polling_unit=None):
        import secrets
        token = secrets.token_urlsafe(32)
        return cls.objects.create(
            token=token,
            invited_email=email,
            staff_number=staff_number,
            role=role,
            assigned_polling_unit=polling_unit,
            invited_by=invited_by,
            expires_at=timezone.now() + timedelta(days=7)
        )

    @property
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"Invitation for {self.invited_email} ({self.role}) - {'Used' if self.is_used else 'Pending'}"

    def save(self, *args, **kwargs):
        if not self.staff_number or self.staff_number.strip() == "":
            from .utils import generate_staff_id
            self.staff_number = generate_staff_id(self.role, '')
        super().save(*args, **kwargs)


class AccreditationApplication(models.Model):
    """
    Portal for Media houses, CSO coalitions, and International Observers to
    submit accreditation applications for review.
    """
    APPLICANT_TYPE_CHOICES = [
        ('media', 'Media House / Broadcaster'),
        ('observer', 'Domestic Observer (CSO)'),
        ('intl_observer', 'International Observer'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    organization_name = models.CharField(max_length=200)
    applicant_type = models.CharField(max_length=20, choices=APPLICANT_TYPE_CHOICES)
    contact_name = models.CharField(max_length=150)
    contact_email = models.EmailField(unique=True)
    contact_phone = models.CharField(max_length=20)
    organization_id = models.CharField(max_length=100, help_text="CAC number, press card ID, or international body reference")
    mandate_description = models.TextField(help_text="Brief description of coverage/oversight mandate")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        ElectoralUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_accreditations'
    )
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.organization_name} ({self.applicant_type}) - {self.status}"


class ElectionClosureApproval(models.Model):
    """
    Multi-signature approval system for closing elections.
    Requires N-of-M returning officers to approve before election transitions to 'closed'.
    Prevents any single officer from unilaterally declaring results.
    """
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='closure_approvals')
    approved_by = models.ForeignKey(ElectoralUser, on_delete=models.CASCADE)
    approved_at = models.DateTimeField(auto_now_add=True)
    digital_signature = models.CharField(max_length=256)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('election', 'approved_by')

    def __str__(self):
        return f"{self.approved_by.full_name} approved closure of {self.election.title}"

