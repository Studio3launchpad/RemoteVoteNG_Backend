import json
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from .models import (
    ElectoralUser, NIMCRecord, PollingUnit, OTPVerification, 
    Election, Candidate, ResultSheet, DisputeLog, ElectionParticipation, AuditLog,
    StaffInvitation, AccreditationApplication
)
from .middleware import get_current_user, get_current_ip

def log_crud_action(sender, instance, action, details=None):
    """
    Helper function to record a CRUD operation in the database.
    """
    if sender == AuditLog:
        return

    user = get_current_user()
    if user:
        try:
            if not ElectoralUser.objects.filter(pk=user.pk).exists():
                user = None
        except Exception:
            user = None

    ip = get_current_ip()


    # Safely convert instance fields to JSON details
    if not details:
        try:
            details_dict = model_to_dict(instance)
            # Serialize non-primitive values to strings
            for k, v in list(details_dict.items()):
                if not isinstance(v, (str, int, float, bool, type(None))):
                    details_dict[k] = str(v)
            details = json.dumps(details_dict)
        except Exception as e:
            details = f"Serialization error: {str(e)}"

    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=sender.__name__,
        object_id=str(instance.pk),
        details=details,
        ip_address=ip
    )


@receiver(post_save)
def post_save_handler(sender, instance, created, **kwargs):
    """
    Intercept saves on tracked models and log them as CREATE or UPDATE.
    """
    tracked_models = [
        ElectoralUser, NIMCRecord, PollingUnit, OTPVerification, 
        Election, Candidate, ResultSheet, DisputeLog, ElectionParticipation
    ]
    if sender in tracked_models:
        action = 'CREATE' if created else 'UPDATE'
        log_crud_action(sender, instance, action)


@receiver(post_delete)
def post_delete_handler(sender, instance, **kwargs):
    """
    Intercept deletes on tracked models and log them as DELETE.
    """
    tracked_models = [
        ElectoralUser, NIMCRecord, PollingUnit, OTPVerification, 
        Election, Candidate, ResultSheet, DisputeLog, ElectionParticipation
    ]
    if sender in tracked_models:
        log_crud_action(sender, instance, 'DELETE')


@receiver(post_save, sender=AccreditationApplication)
def accreditation_application_post_save(sender, instance, created, **kwargs):
    """
    Send emails depending on updates performed on the AccreditationApplication.
    """
    # Avoid triggering logic on creation if it starts pending
    if created and instance.status == 'pending':
        return

    if instance.status == 'approved':
        # Prevent double-processing if invitation is already generated
        invitation_exists = StaffInvitation.objects.filter(invited_email=instance.contact_email).exists()
        if not invitation_exists:
            # Generate staff number
            org_code = instance.organization_name[:4].upper().replace(' ', '')
            staff_number = f"{org_code}-{instance.applicant_type.upper()[:3]}-{instance.id}"
            role = 'media' if instance.applicant_type == 'media' else 'observer'

            current_user = get_current_user()

            # Create StaffInvitation
            invitation = StaffInvitation.create_invitation(
                email=instance.contact_email,
                staff_number=staff_number,
                role=role,
                invited_by=current_user,
            )

            # Send onboarding invitation email
            from .brevo import send_staff_invitation_email
            send_staff_invitation_email(
                email=invitation.invited_email,
                role_display=invitation.get_role_display(),
                staff_number=invitation.staff_number,
                token=invitation.token
            )

            # Send accreditation approval notification
            from .brevo import send_accreditation_approved_email
            send_accreditation_approved_email(
                email=instance.contact_email,
                org_name=instance.organization_name,
                role=role
            )

    elif instance.status == 'rejected':
        from .brevo import send_accreditation_rejected_email
        send_accreditation_rejected_email(
            email=instance.contact_email,
            org_name=instance.organization_name,
            reason=instance.review_notes
        )

