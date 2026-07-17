from rest_framework import serializers
from .models import (
    NIMCRecord, ElectoralUser, OTPVerification, Election, 
    Candidate, ElectionParticipation, ResultSheet, DisputeLog, AuditLog,
    StaffInvitation, AccreditationApplication, ElectionClosureApproval, PollingUnit,
    VoterRegistrationRecord
)
from datetime import date
import uuid
import re

class NIMCRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = NIMCRecord
        fields = ['id', 'nin', 'full_name', 'state', 'lga', 'biometric_hash']
        extra_kwargs = {
            'biometric_hash': {'required': False}
        }

    def create(self, validated_data):
        if 'biometric_hash' not in validated_data or not validated_data['biometric_hash']:
            validated_data['biometric_hash'] = 'mock_biometric_hash_xyz_123'
        return super().create(validated_data)


class VoterRegistrationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoterRegistrationRecord
        fields = [
            'id', 'vrn', 'nin', 'full_name', 'date_of_birth',
            'gender', 'state', 'lga', 'ward', 'polling_unit_code',
            'is_claimed', 'claimed_at'
        ]
        read_only_fields = ['is_claimed', 'claimed_at']


class PollingUnitSerializer(serializers.ModelSerializer):
    presiding_officer_name = serializers.CharField(source='presiding_officer.full_name', read_only=True, allow_null=True)
    collation_officer_name = serializers.CharField(source='collation_officer.full_name', read_only=True, allow_null=True)

    class Meta:
        model = PollingUnit
        fields = [
            'id', 'name', 'ward', 'lga', 'state', 'registered_voters_count',
            'presiding_officer', 'presiding_officer_name',
            'collation_officer', 'collation_officer_name'
        ]
        extra_kwargs = {
            'id': {'required': False, 'allow_blank': True}
        }


class ElectoralUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElectoralUser
        fields = [
            'username', 'staff_number', 'full_name', 'email', 
            'state', 'lga', 'role', 'is_verified', 'language', 'voter_id'
        ]
        extra_kwargs = {
            'username': {'read_only': True}
        }


class RegisterSerializer(serializers.ModelSerializer):
    nin = serializers.CharField(max_length=11, min_length=11, write_only=True)
    vrn = serializers.CharField(max_length=20, write_only=True)
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = ElectoralUser
        fields = ['nin', 'vrn', 'password']

    def validate_nin(self, value):
        if not value.isdigit() or len(value) != 11:
            raise serializers.ValidationError("NIN must be exactly 11 digits.")
        if ElectoralUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("A voter with this NIN is already registered.")
        return value

    def validate(self, data):
        nin = data.get('nin')
        vrn = data.get('vrn')

        # Cross-validate VRN + NIN against the voter register
        try:
            record = VoterRegistrationRecord.objects.get(vrn=vrn)
        except VoterRegistrationRecord.DoesNotExist:
            raise serializers.ValidationError({
                "vrn": "Voter Registration Number (VRN) not found in the INEC voter register."
            })

        if record.nin != nin:
            raise serializers.ValidationError({
                "vrn": "The VRN provided does not match your NIN in the INEC voter register."
            })

        if record.is_claimed:
            raise serializers.ValidationError({
                "vrn": "This VRN has already been used to create an account. Contact INEC if this is an error."
            })

        # Attach record to context for use in create()
        self._vrn_record = record
        return data

    def create(self, validated_data):
        nin = validated_data['nin']
        password = validated_data['password']
        vrn_record = self._vrn_record

        # Bypass create_user to prevent it from normalizing email=None to ""
        # and saving it immediately (which triggers the unique constraint).
        user = ElectoralUser(
            username=nin,
            email=None,
            role='voter',
            is_verified=True,   # Auto-verify voters (no email/OTP)
            full_name=vrn_record.full_name,
            state=vrn_record.state,
            lga=vrn_record.lga,
            date_of_birth=vrn_record.date_of_birth,
        )
        user.set_password(password)
        user.save()

        # Mark the VRN record as claimed
        from django.utils import timezone
        vrn_record.is_claimed = True
        vrn_record.claimed_at = timezone.now()
        vrn_record.save(update_fields=['is_claimed', 'claimed_at'])

        return user

    #     if data['password'] != data['confirm_password']:


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ['id', 'name', 'party', 'party_abbr', 'party_logo', 'color', 'manifesto', 'running_mate', 'votes_count']


class ElectionSerializer(serializers.ModelSerializer):
    candidates = CandidateSerializer(many=True, read_only=True)
    has_voted = serializers.SerializerMethodField()
    approval_count = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    election_type_display = serializers.CharField(source='get_election_type_display', read_only=True)
    candidate_count = serializers.SerializerMethodField()

    class Meta:
        model = Election
        fields = [
            'id', 'title', 'election_type', 'election_type_display',
            'description', 'date', 'status', 'status_display',
            'eligible_states', 'created_by', 'created_by_name', 'created_at',
            'candidates', 'candidate_count', 'has_voted', 'approval_count',
        ]

    def get_has_voted(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return ElectionParticipation.objects.filter(voter=request.user, election=obj).exists()
        return False

    def get_approval_count(self, obj):
        return obj.closure_approvals.count()

    def get_candidate_count(self, obj):
        return obj.candidates.count()


class ElectionCreateSerializer(serializers.Serializer):
    """
    Used by Commissioners to draft a new election.
    Generates a slug-safe ID from the title automatically.
    """
    title = serializers.CharField(max_length=200)
    election_type = serializers.ChoiceField(choices=Election.ELECTION_TYPE_CHOICES)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    date = serializers.DateField()
    eligible_states = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Title cannot be blank.")
        # Generate a deterministic ID from the title
        slug = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
        if Election.objects.filter(id=slug).exists():
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
        self._generated_id = slug
        return value

    def create(self, validated_data):
        title = validated_data['title']
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        if Election.objects.filter(id=slug).exists():
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        return Election.objects.create(
            id=slug,
            title=title,
            election_type=validated_data['election_type'],
            description=validated_data.get('description', ''),
            date=validated_data['date'],
            eligible_states=validated_data.get('eligible_states', []),
            status='drafted',
            created_by=self.context['request'].user
        )


class ElectionUpdateSerializer(serializers.ModelSerializer):
    """
    Allows Commissioners to edit draft/upcoming elections.
    Active and closed elections are locked from editing.
    """
    eligible_states = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
        allow_empty=True
    )

    class Meta:
        model = Election
        fields = ['title', 'election_type', 'description', 'date', 'eligible_states']

    def validate(self, attrs):
        if self.instance and self.instance.status in ['active', 'collation', 'closed']:
            raise serializers.ValidationError(
                f"Cannot edit an election that is currently '{self.instance.status}'. "
                "Only drafted or upcoming elections can be modified."
            )
        return attrs


class CandidateCreateSerializer(serializers.Serializer):
    """
    Used by Commissioners to register candidates for a specific election.
    """
    name = serializers.CharField(max_length=150)
    party = serializers.CharField(max_length=150)
    party_abbr = serializers.CharField(max_length=20)
    color = serializers.CharField(max_length=10, default='#1565c0')
    manifesto = serializers.CharField()
    running_mate = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    legal_affidavit_url = serializers.URLField(required=False, allow_blank=True)

    def validate_party_abbr(self, value):
        return value.upper().strip()

    def create(self, validated_data):
        import secrets
        election = self.context['election']
        
        # Generate a highly secure, unpredictable, but short candidate ID
        # Format: CAN-[8 random hex characters] -> e.g. CAN-A1B2C3D4
        candidate_id = f"CAN-{secrets.token_hex(4).upper()}"
        while Candidate.objects.filter(id=candidate_id).exists():
            candidate_id = f"CAN-{secrets.token_hex(4).upper()}"

        return Candidate.objects.create(
            id=candidate_id,
            election=election,
            name=validated_data['name'],
            party=validated_data['party'],
            party_abbr=validated_data['party_abbr'],
            color=validated_data.get('color', '#1565c0'),
            manifesto=validated_data['manifesto'],
            running_mate=validated_data.get('running_mate', ''),
            legal_affidavit_url=validated_data.get('legal_affidavit_url', '') or None,
        )


class ResultSheetSerializer(serializers.ModelSerializer):
    presiding_officer_name = serializers.CharField(source='presiding_officer.full_name', read_only=True)
    polling_unit_name = serializers.CharField(source='polling_unit.name', read_only=True)

    class Meta:
        model = ResultSheet
        fields = [
            'id', 'election', 'polling_unit', 'polling_unit_name', 
            'presiding_officer', 'presiding_officer_name', 'scanned_form_url', 
            'accredited_voters', 'total_votes_cast', 'po_digital_signature', 
            'is_countersigned_by_agents', 'flagged_for_overvoting', 'timestamp'
        ]
        read_only_fields = ['presiding_officer', 'flagged_for_overvoting']


class DisputeLogSerializer(serializers.ModelSerializer):
    raised_by_name = serializers.CharField(source='raised_by.full_name', read_only=True)
    polling_unit_name = serializers.CharField(source='polling_unit.name', read_only=True)

    class Meta:
        model = DisputeLog
        fields = [
            'id', 'polling_unit', 'polling_unit_name', 'raised_by', 
            'raised_by_name', 'description', 'is_resolved', 'timestamp'
        ]
        read_only_fields = ['raised_by']


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    role = serializers.CharField(source='user.role', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'username', 'role', 'action', 'model_name', 
            'object_id', 'details', 'timestamp', 'ip_address'
        ]

    def get_username(self, obj):
        if obj.user:
            return obj.user.staff_number if obj.user.staff_number else obj.user.username
        return "System"


class StaffInvitationSerializer(serializers.ModelSerializer):
    invited_by_name = serializers.CharField(source='invited_by.full_name', read_only=True)
    polling_unit_name = serializers.CharField(source='assigned_polling_unit.name', read_only=True, allow_null=True)
    is_valid = serializers.ReadOnlyField()

    class Meta:
        model = StaffInvitation
        fields = [
            'id', 'token', 'invited_email', 'staff_number', 'role',
            'assigned_polling_unit', 'polling_unit_name', 'invited_by',
            'invited_by_name', 'is_used', 'is_valid', 'created_at', 'expires_at'
        ]
        read_only_fields = ['token', 'invited_by', 'is_used', 'created_at']


class AccreditationApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccreditationApplication
        fields = [
            'id', 'organization_name', 'applicant_type', 'contact_name',
            'contact_email', 'contact_phone', 'organization_id',
            'mandate_description', 'status', 'review_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['status', 'review_notes', 'created_at', 'updated_at']


class ElectionClosureApprovalSerializer(serializers.ModelSerializer):
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)
    approved_by_staff = serializers.CharField(source='approved_by.staff_number', read_only=True)

    class Meta:
        model = ElectionClosureApproval
        fields = [
            'id', 'election', 'approved_by', 'approved_by_name', 
            'approved_by_staff', 'approved_at', 'digital_signature', 'notes'
        ]
        read_only_fields = ['approved_by', 'approved_at']
