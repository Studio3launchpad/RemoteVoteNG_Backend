from django.contrib import admin
from unfold.admin import ModelAdmin
from django.contrib.admin.forms import AdminAuthenticationForm
from django import forms
from .models import (
    ElectoralUser, NIMCRecord, PollingUnit, OTPVerification, 
    Election, Candidate, ResultSheet, DisputeLog, ElectionParticipation, AuditLog,
    StaffInvitation, AccreditationApplication, ElectionClosureApproval, VoterRegistrationRecord
)

# Custom Admin Login Form to use Staff ID label
class StaffAdminAuthenticationForm(AdminAuthenticationForm):
    username = forms.CharField(
        label="Staff ID / NIN", 
        help_text="Login using your Staff ID (for election officials) or NIN.",
        widget=forms.TextInput(attrs={'autofocus': True, 'placeholder': 'e.g., STAFF-PO or 11111111111'})
    )

# Assign custom form to default admin site
admin.site.login_form = StaffAdminAuthenticationForm
admin.site.site_header = "RemoteVote NG - Electoral Management Admin"
admin.site.site_title = "RemoteVote NG Admin Portal"
admin.site.index_title = "Control Panel & Audit Dashboard"


@admin.register(ElectoralUser)
class ElectoralUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'staff_number', 'full_name', 'email', 'role', 'is_verified', 'is_staff']
    list_filter = ['role', 'is_verified', 'is_staff', 'state']
    search_fields = ['username', 'staff_number', 'full_name', 'email']
    ordering = ['role', 'username']


@admin.register(NIMCRecord)
class NIMCRecordAdmin(ModelAdmin):
    list_display = ['nin', 'full_name', 'state', 'lga']
    list_filter = ['state']
    search_fields = ['nin', 'full_name']


@admin.register(VoterRegistrationRecord)
class VoterRegistrationRecordAdmin(ModelAdmin):
    list_display = ['vrn', 'full_name', 'nin', 'state', 'lga', 'ward', 'gender', 'is_claimed', 'claimed_at']
    list_filter = ['state', 'gender', 'is_claimed']
    search_fields = ['vrn', 'nin', 'full_name']
    readonly_fields = ['is_claimed', 'claimed_at']
    ordering = ['state', 'lga']

    def has_change_permission(self, request, obj=None):
        # Only superusers can modify the voter register
        return request.user.is_superuser


@admin.register(PollingUnit)
class PollingUnitAdmin(ModelAdmin):
    list_display = ['id', 'name', 'ward', 'lga', 'state', 'registered_voters_count']
    list_filter = ['state', 'lga']
    search_fields = ['id', 'name', 'ward']


@admin.register(Election)
class ElectionAdmin(ModelAdmin):
    list_display = ['id', 'title', 'date', 'status', 'blockchain_contract_address']
    list_filter = ['status', 'date']
    search_fields = ['id', 'title']


@admin.register(Candidate)
class CandidateAdmin(ModelAdmin):
    list_display = ['id', 'name', 'party_abbr', 'election', 'votes_count']
    list_filter = ['election', 'party_abbr']
    search_fields = ['id', 'name', 'party']


@admin.register(ResultSheet)
class ResultSheetAdmin(ModelAdmin):
    list_display = ['id', 'election', 'polling_unit', 'presiding_officer', 'total_votes_cast', 'flagged_for_overvoting', 'timestamp']
    list_filter = ['election', 'flagged_for_overvoting', 'timestamp']
    search_fields = ['polling_unit__name', 'presiding_officer__full_name']


@admin.register(DisputeLog)
class DisputeLogAdmin(ModelAdmin):
    list_display = ['id', 'polling_unit', 'raised_by', 'is_resolved', 'timestamp']
    list_filter = ['is_resolved', 'timestamp']
    search_fields = ['polling_unit__name', 'description']


@admin.register(ElectionParticipation)
class ElectionParticipationAdmin(ModelAdmin):
    list_display = ['voter', 'election', 'voted_at', 'cryptographic_receipt']
    list_filter = ['election', 'voted_at']
    search_fields = ['voter__username', 'cryptographic_receipt']


@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    """
    Read-only Audit Log list to prevent administrative editing of logs.
    """
    list_display = ['user', 'action', 'model_name', 'object_id', 'timestamp', 'ip_address']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['user__username', 'user__staffid', 'model_name', 'object_id', 'details']
    
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StaffInvitation)
class StaffInvitationAdmin(admin.ModelAdmin):
    list_display = ['staff_number', 'invited_email', 'role', 'invited_by', 'is_used', 'created_at', 'expires_at']
    list_filter = ['role', 'is_used', 'created_at']
    search_fields = ['staff_id', 'invited_email', 'token']
    readonly_fields = ['token', 'created_at']

    def has_change_permission(self, request, obj=None):
        # Invitations should be read-only once created (except for is_used flag by ICT staff)
        return request.user.is_superuser


@admin.register(AccreditationApplication)
class AccreditationApplicationAdmin(ModelAdmin):
    list_display = ['organization_name', 'applicant_type', 'contact_name', 'contact_email', 'status', 'created_at']
    list_filter = ['applicant_type', 'status', 'created_at']
    search_fields = ['organization_name', 'contact_name', 'contact_email', 'organization_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ElectionClosureApproval)
class ElectionClosureApprovalAdmin(ModelAdmin):
    list_display = ['election', 'approved_by', 'approved_at', 'digital_signature']
    list_filter = ['election', 'approved_at']
    search_fields = ['approved_by__full_name', 'approved_by__staffid', 'digital_signature']
    readonly_fields = ['approved_at', 'digital_signature']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

