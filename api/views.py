from django.shortcuts import render, get_object_or_404
from rest_framework import status, views, permissions, generics
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db import transaction, IntegrityError
from django.db.models import F, Q
from django.utils import timezone
from django.conf import settings
from .models import (
    NIMCRecord, ElectoralUser, OTPVerification, Election, 
    Candidate, ElectionParticipation, ResultSheet, DisputeLog, AuditLog, PollingUnit,
    StaffInvitation, AccreditationApplication, ElectionClosureApproval
)
from .serializers import (
    RegisterSerializer, ElectoralUserSerializer, ElectionSerializer, 
    CandidateSerializer, ResultSheetSerializer, DisputeLogSerializer, AuditLogSerializer,
    StaffInvitationSerializer, AccreditationApplicationSerializer, ElectionClosureApprovalSerializer,
    ElectionCreateSerializer, ElectionUpdateSerializer, CandidateCreateSerializer, PollingUnitSerializer,
    NIMCRecordSerializer
)
from .brevo import send_otp_email
import random
import secrets


class RegisterView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                otp = OTPVerification.generate_otp(user, 'signup')
                email_sent = send_otp_email(user, otp.code, 'signup')
                return Response({
                    "message": "Registration successful. Verification email sent.",
                    "nin": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "email_sent": email_sent,
                    "otp_code_preview": otp.code if settings.BREVO_API_KEY in [None, 'mock', ''] else None
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        nin = request.data.get('nin')
        code = request.data.get('code')
        purpose = request.data.get('purpose', 'signup')

        if not nin or not code:
            return Response({"error": "NIN and OTP code are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(ElectoralUser, username=nin)
        otp_query = OTPVerification.objects.filter(
            user=user, code=code, purpose=purpose,
            is_used=False, expires_at__gt=timezone.now()
        )

        if not otp_query.exists():
            return Response({"error": "Invalid or expired verification code."}, status=status.HTTP_400_BAD_REQUEST)

        otp = otp_query.first()
        otp.is_used = True
        otp.save()

        if purpose == 'signup':
            user.is_verified = True
            user.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "message": "Account successfully verified.",
                "token": token.key,
                "voter": ElectoralUserSerializer(user).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "message": "OTP verified successfully. You may now reset your password.",
                "nin": nin, "code": code
            }, status=status.HTTP_200_OK)


class LoginView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        identifier = request.data.get('nin') or request.data.get('username') or request.data.get('staff_number')
        password = request.data.get('password')

        if not identifier or not password:
            return Response({"error": "Login ID and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=identifier, password=password)
        if not user:
            return Response({"error": "Invalid login credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_verified and user.role in ['voter', 'prospective']:
            otp = OTPVerification.generate_otp(user, 'signup')
            send_otp_email(user, otp.code, 'signup')
            return Response({
                "error": "Account not verified.",
                "code": "unverified",
                "nin": user.username,
                "email": user.email,
                "message": "A new verification code has been sent to your email."
            }, status=status.HTTP_403_FORBIDDEN)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "voter": ElectoralUserSerializer(user).data}, status=status.HTTP_200_OK)


class ForgotPasswordView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        nin = request.data.get('nin')
        if not nin:
            return Response({"error": "NIN is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = ElectoralUser.objects.get(username=nin)
            otp = OTPVerification.generate_otp(user, 'reset')
            send_otp_email(user, otp.code, 'reset')
            return Response({
                "message": "Password reset code sent to your registered email.",
                "nin": nin, "email": user.email
            }, status=status.HTTP_200_OK)
        except ElectoralUser.DoesNotExist:
            return Response({"error": "No registered voter found with this NIN."}, status=status.HTTP_404_NOT_FOUND)


class ResetPasswordView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        nin = request.data.get('nin')
        code = request.data.get('code')
        password = request.data.get('password')

        if not nin or not code or not password:
            return Response({"error": "NIN, verification code, and new password are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(ElectoralUser, username=nin)
        otp_query = OTPVerification.objects.filter(
            user=user, code=code, purpose='reset',
            is_used=False, expires_at__gt=timezone.now()
        )

        if not otp_query.exists():
            return Response({"error": "Invalid or expired reset code."}, status=status.HTTP_400_BAD_REQUEST)

        otp = otp_query.first()
        otp.is_used = True
        otp.save()
        user.set_password(password)
        user.save()
        return Response({"message": "Password reset successfully. You can now sign in."}, status=status.HTTP_200_OK)


class ProfileView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(ElectoralUserSerializer(request.user).data, status=status.HTTP_200_OK)

    def patch(self, request):
        user = request.user
        language = request.data.get('language')
        if language:
            user.language = language
            user.save()
            return Response(ElectoralUserSerializer(user).data, status=status.HTTP_200_OK)
        return Response({"error": "No update fields provided."}, status=status.HTTP_400_BAD_REQUEST)


class ElectionListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Drafted elections are internal — hidden from voters, field staff, and public viewers.
        # Only commissioners and auditors can see all elections via /commissioner/elections/
        public_statuses = ['upcoming', 'active', 'collation', 'closed']
        elections = Election.objects.filter(status__in=public_statuses).prefetch_related('candidates')
        serializer = ElectionSerializer(elections, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ElectionDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        election = get_object_or_404(Election, id=pk)
        serializer = ElectionSerializer(election, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CastVoteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        election_id = request.data.get('election_id')
        candidate_id = request.data.get('candidate_id')

        if not election_id or not candidate_id:
            return Response({"error": "Election ID and Candidate ID are required."}, status=status.HTTP_400_BAD_REQUEST)

        election = get_object_or_404(Election, id=election_id)
        candidate = get_object_or_404(Candidate, id=candidate_id, election=election)

        if not election.can_accept_votes:
            return Response(
                {"error": f"This election is not currently open for voting (status: '{election.status}')."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                ElectionParticipation.objects.create(voter=request.user, election=election)
                Candidate.objects.filter(id=candidate_id).update(votes_count=F('votes_count') + 1)
        except IntegrityError:
            return Response({"error": "You have already cast a ballot in this election."}, status=status.HTTP_400_BAD_REQUEST)

        chars = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
        out = "".join(random.choice(chars) for _ in range(12))
        receipt = f"RVNG-{out[:4]}-{out[4:8]}-{out[8:]}"
        return Response({"message": "Ballot cast successfully.", "receipt": receipt}, status=status.HTTP_200_OK)


# --- STAFF ROLE-BASED ACCESS VIEWS ---

class ResultSheetListCreateView(generics.ListCreateAPIView):
    serializer_class = ResultSheetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['co', 'ro', 'auditor', 'observer', 'agent']:
            return ResultSheet.objects.all().order_by('-timestamp')
        return ResultSheet.objects.filter(presiding_officer=user).order_by('-timestamp')

    def perform_create(self, serializer):
        serializer.save(presiding_officer=self.request.user)


class ResultSheetVerifyView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if request.user.role not in ['co', 'ro']:
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        sheet = get_object_or_404(ResultSheet, id=pk)
        action = request.data.get('action')
        if action == 'flag':
            sheet.flagged_for_overvoting = True
            sheet.save()
            return Response({"message": "Result sheet FLAGGED for audit."}, status=status.HTTP_200_OK)
        else:
            sheet.flagged_for_overvoting = False
            sheet.save()
            return Response({"message": "Result sheet verified and approved."}, status=status.HTTP_200_OK)


class DisputeLogListCreateView(generics.ListCreateAPIView):
    serializer_class = DisputeLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DisputeLog.objects.all().order_by('-timestamp')

    def perform_create(self, serializer):
        serializer.save(raised_by=self.request.user)


class DisputeResolveView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if request.user.role not in ['po', 'co', 'ro']:
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        dispute = get_object_or_404(DisputeLog, id=pk)
        dispute.is_resolved = True
        dispute.save()
        return Response({"message": "Dispute marked as RESOLVED."}, status=status.HTTP_200_OK)


class ApproveElectionClosureView(views.APIView):
    """
    Multi-signature election closure: an RO submits their approval.
    Only once enough ROs have signed does the election transition to 'closed'.
    Threshold configured via ELECTION_CLOSURE_SIGNATURES_REQUIRED in settings.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != 'ro':
            return Response({"error": "Only Returning Officers can approve election closure."}, status=status.HTTP_403_FORBIDDEN)

        election = get_object_or_404(Election, id=pk)

        if election.status == 'closed':
            return Response({"error": "This election has already been closed."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if already signed
        if ElectionClosureApproval.objects.filter(election=election, approved_by=request.user).exists():
            return Response({"error": "You have already submitted your closure approval for this election."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate digital signature
        digital_sig = f"SIG-{request.user.staff_number}-{election.id}-{secrets.token_hex(8).upper()}"

        # Record this RO's approval
        approval = ElectionClosureApproval.objects.create(
            election=election,
            approved_by=request.user,
            digital_signature=digital_sig,
            notes=request.data.get('notes', '')
        )

        # Check if we've reached the required threshold
        approval_count = election.closure_approvals.count()
        required = getattr(settings, 'ELECTION_CLOSURE_SIGNATURES_REQUIRED', 2)

        if approval_count >= required:
            election.status = 'closed'
            election.save()
            return Response({
                "message": f"Election '{election.title}' has been officially CLOSED. {approval_count}/{required} approvals received. Results are now final and publicly published.",
                "status": "closed",
                "approvals": approval_count,
                "required": required,
                "your_signature": digital_sig
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "message": f"Your closure approval has been recorded. Awaiting {required - approval_count} more approval(s) from other Returning Officers.",
                "status": election.status,
                "approvals": approval_count,
                "required": required,
                "your_signature": digital_sig
            }, status=status.HTTP_202_ACCEPTED)


class ElectionClosureApprovalsView(views.APIView):
    """
    Returns the list of closure approvals for a given election.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ['ro', 'auditor']:
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        election = get_object_or_404(Election, id=pk)
        approvals = ElectionClosureApproval.objects.filter(election=election).select_related('approved_by')
        required = getattr(settings, 'ELECTION_CLOSURE_SIGNATURES_REQUIRED', 2)
        return Response({
            "election": election.title,
            "status": election.status,
            "approvals_received": approvals.count(),
            "approvals_required": required,
            "signatures": ElectionClosureApprovalSerializer(approvals, many=True).data
        }, status=status.HTTP_200_OK)


class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'auditor':
            return AuditLog.objects.none()
        return AuditLog.objects.all().order_by('-timestamp')


class PollingUnitListCreateView(generics.ListCreateAPIView):
    serializer_class = PollingUnitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'secretary':
            return PollingUnit.objects.all().order_by('id')
        if user.role == 'commissioner':
            return PollingUnit.objects.filter(state=user.state).order_by('id')
        return PollingUnit.objects.all().order_by('id')

    def post(self, request, *args, **kwargs):
        if request.user.role != 'commissioner':
            return Response({"error": "Only INEC Electoral Commissioners can create Polling Units."}, status=status.HTTP_403_FORBIDDEN)
        
        is_many = isinstance(request.data, list)
        if is_many:
            for item in request.data:
                if item.get('state') != request.user.state:
                    return Response({"error": f"You can only create Polling Units for your assigned state ({request.user.state}). Found item with state '{item.get('state')}'."}, status=status.HTTP_403_FORBIDDEN)
            serializer = self.get_serializer(data=request.data, many=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            if request.data.get('state') != request.user.state:
                return Response({"error": f"You can only create Polling Units for your assigned state ({request.user.state})."}, status=status.HTTP_403_FORBIDDEN)
            return super().post(request, *args, **kwargs)



class PollingUnitManageView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PollingUnit.objects.all()
    serializer_class = PollingUnitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'secretary':
            return PollingUnit.objects.all()
        if user.role == 'commissioner':
            return PollingUnit.objects.filter(state=user.state)
        return PollingUnit.objects.all()

    def patch(self, request, *args, **kwargs):
        if request.user.role != 'commissioner':
            return Response({"error": "Only INEC Electoral Commissioners can update Polling Units."}, status=status.HTTP_403_FORBIDDEN)
        obj = self.get_object()
        if obj.state != request.user.state:
            return Response({"error": "You do not have permission to manage Polling Units outside your state."}, status=status.HTTP_403_FORBIDDEN)
        return super().patch(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        if request.user.role != 'commissioner':
            return Response({"error": "Only INEC Electoral Commissioners can update Polling Units."}, status=status.HTTP_403_FORBIDDEN)
        obj = self.get_object()
        if obj.state != request.user.state:
            return Response({"error": "You do not have permission to manage Polling Units outside your state."}, status=status.HTTP_403_FORBIDDEN)
        return super().put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if request.user.role != 'commissioner':
            return Response({"error": "Only INEC Electoral Commissioners can delete Polling Units."}, status=status.HTTP_403_FORBIDDEN)
        obj = self.get_object()
        if obj.state != request.user.state:
            return Response({"error": "You do not have permission to delete Polling Units outside your state."}, status=status.HTTP_403_FORBIDDEN)
        return super().delete(request, *args, **kwargs)


class NIMCRecordListCreateView(generics.ListCreateAPIView):
    serializer_class = NIMCRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'secretary':
            return NIMCRecord.objects.all().order_by('nin')
        if user.role != 'commissioner':
            return NIMCRecord.objects.none()
        return NIMCRecord.objects.filter(state=user.state).order_by('nin')

    def post(self, request, *args, **kwargs):
        if request.user.role not in ['commissioner', 'secretary']:
            return Response({"error": "Only INEC Electoral Commissioners or Secretaries can manage the NIMC database registry."}, status=status.HTTP_403_FORBIDDEN)
        
        is_many = isinstance(request.data, list)
        if is_many:
            if request.user.role == 'commissioner':
                for item in request.data:
                    if item.get('state') != request.user.state:
                        return Response({"error": f"You can only add NIMC records for your assigned state ({request.user.state}). Found item with state '{item.get('state')}'."}, status=status.HTTP_403_FORBIDDEN)
            serializer = self.get_serializer(data=request.data, many=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            if request.user.role == 'commissioner' and request.data.get('state') != request.user.state:
                return Response({"error": f"You can only add NIMC records for your assigned state: {request.user.state}."}, status=status.HTTP_403_FORBIDDEN)
            return super().post(request, *args, **kwargs)



class NIMCRecordManageView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NIMCRecord.objects.all()
    serializer_class = NIMCRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'secretary':
            return NIMCRecord.objects.all()
        if user.role == 'commissioner':
            return NIMCRecord.objects.filter(state=user.state)
        return NIMCRecord.objects.none()

    def patch(self, request, *args, **kwargs):
        if request.user.role not in ['commissioner', 'secretary']:
            return Response({"error": "Only INEC Electoral Commissioners or Secretaries can manage the NIMC database registry."}, status=status.HTTP_403_FORBIDDEN)
        obj = self.get_object()
        if request.user.role == 'commissioner' and obj.state != request.user.state:
            return Response({"error": "You do not have permission to manage records outside your state."}, status=status.HTTP_403_FORBIDDEN)
        return super().patch(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        if request.user.role not in ['commissioner', 'secretary']:
            return Response({"error": "Only INEC Electoral Commissioners or Secretaries can manage the NIMC database registry."}, status=status.HTTP_403_FORBIDDEN)
        obj = self.get_object()
        if request.user.role == 'commissioner' and obj.state != request.user.state:
            return Response({"error": "You do not have permission to manage records outside your state."}, status=status.HTTP_403_FORBIDDEN)
        return super().put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        if request.user.role not in ['commissioner', 'secretary']:
            return Response({"error": "Only INEC Electoral Commissioners or Secretaries can manage the NIMC database registry."}, status=status.HTTP_403_FORBIDDEN)
        obj = self.get_object()
        if request.user.role == 'commissioner' and obj.state != request.user.state:
            return Response({"error": "You do not have permission to manage records outside your state."}, status=status.HTTP_403_FORBIDDEN)
        return super().delete(request, *args, **kwargs)


class ResendStaffInvitationView(views.APIView):
    """
    INEC Electoral Commissioners or Secretaries can resend a pending staff invitation email.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if request.user.role not in ['commissioner', 'secretary']:
            return Response({"error": "Only INEC Electoral Commissioners or Secretaries can resend invitations."}, status=status.HTTP_403_FORBIDDEN)

        invitation = get_object_or_404(StaffInvitation, id=pk)
        if request.user.role == 'commissioner':
            if invitation.assigned_polling_unit and invitation.assigned_polling_unit.state != request.user.state:
                return Response({"error": "You do not have permission to manage invitations outside your state."}, status=status.HTTP_403_FORBIDDEN)

        if invitation.is_used:
            return Response({"error": "This invitation has already been used."}, status=status.HTTP_400_BAD_REQUEST)

        from .brevo import send_staff_invitation_email
        send_staff_invitation_email(
            email=invitation.invited_email,
            role_display=invitation.get_role_display(),
            staff_number=invitation.staff_number,
            token=invitation.token
        )
        return Response({"message": f"Invitation email resent successfully to {invitation.invited_email}."}, status=status.HTTP_200_OK)



# ============================================================
# ONBOARDING VIEWS
# ============================================================

class SendStaffInvitationView(views.APIView):
    """
    INEC Electoral Commissioners or Secretaries can send email invitations to electoral officials.
    The invitation contains a secure token for account activation.
    Supports bulk list payloads.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role not in ['commissioner', 'secretary']:
            return Response({"error": "Only INEC Electoral Commissioners or Secretaries can send staff invitations."}, status=status.HTTP_403_FORBIDDEN)

        is_many = isinstance(request.data, list)
        items = request.data if is_many else [request.data]
        
        if not items:
            return Response({"error": "No invitation data provided."}, status=status.HTTP_400_BAD_REQUEST)

        valid_roles = ['commissioner', 'secretary', 'po', 'apo', 'spo', 'co', 'ro', 'auditor']
        results = []
        
        from django.db import transaction
        try:
            with transaction.atomic():
                for idx, data in enumerate(items):
                    email = data.get('email')
                    role = data.get('role')
                    polling_unit_id = data.get('polling_unit_id')

                    if not email or not role:
                        raise ValueError(f"Email and role are required (Index {idx}).")

                    if role not in valid_roles:
                        raise ValueError(f"Invalid role '{role}' at index {idx}. Must be one of: {', '.join(valid_roles)}")

                    # Autogenerate staff number
                    role_prefix = role.upper()
                    staff_number = f"STAFF-{role_prefix}-{random.randint(100000, 999999)}"
                    while ElectoralUser.objects.filter(staff_number=staff_number).exists() or StaffInvitation.objects.filter(staff_number=staff_number).exists():
                        staff_number = f"STAFF-{role_prefix}-{random.randint(100000, 999999)}"

                    polling_unit = None
                    if polling_unit_id:
                        try:
                            polling_unit = PollingUnit.objects.get(id=polling_unit_id)
                        except PollingUnit.DoesNotExist:
                            raise ValueError(f"Polling unit with ID '{polling_unit_id}' not found (Index {idx}).")
                        
                        if request.user.role == 'commissioner' and polling_unit.state != request.user.state:
                            raise ValueError(f"You can only invite staff to polling units in your assigned state ({request.user.state}). Found index {idx} state '{polling_unit.state}'.")
                    
                    invitation = StaffInvitation.create_invitation(
                        email=email,
                        role=role,
                        staff_number=staff_number,
                        invited_by=request.user,
                        polling_unit=polling_unit
                    )

                    # Send invitation email using Brevo
                    try:
                        from .brevo import send_staff_invitation_email
                        send_staff_invitation_email(
                            email=invitation.invited_email,
                            role_display=invitation.get_role_display(),
                            staff_number=invitation.staff_number,
                            token=invitation.token
                        )
                    except Exception as e:
                        print(f"Failed to send email to {email}: {e}")

                    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
                    activation_link = f"{frontend_url}/onboard?token={invitation.token}"
                    
                    results.append({
                        "email": invitation.invited_email,
                        "role": invitation.role,
                        "staff_number": invitation.staff_number,
                        "invitation_token": invitation.token,
                        "activation_link": activation_link,
                        "expires_at": invitation.expires_at
                    })
        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"An error occurred during bulk invitation: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if is_many:
            return Response({
                "message": f"Successfully sent {len(results)} staff invitations.",
                "invitations": results
            }, status=status.HTTP_201_CREATED)
        else:
            res = results[0]
            return Response({
                "message": f"Invitation sent to {res['email']} for role '{res['role']}'.",
                "invitation_token": res['invitation_token'],
                "activation_link": res['activation_link'],
                "expires_at": res['expires_at']
            }, status=status.HTTP_201_CREATED)



class StaffInvitationListView(generics.ListAPIView):
    """
    Electoral Commissioners or Secretaries can view all invitations sent.
    """
    serializer_class = StaffInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'secretary':
            return StaffInvitation.objects.all().order_by('-created_at')
        if user.role != 'commissioner':
            return StaffInvitation.objects.none()
        return StaffInvitation.objects.filter(
            Q(assigned_polling_unit__state=user.state) |
            Q(assigned_polling_unit__isnull=True, invited_by__state=user.state)
        ).order_by('-created_at')


class AcceptStaffInvitationView(views.APIView):
    """
    Officials use their invitation token + NIN to activate their staff account.
    This replaces the need for someone to manually create accounts for them.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        """Validate and return invitation details."""
        invitation = get_object_or_404(StaffInvitation, token=token)
        if not invitation.is_valid:
            return Response({"error": "This invitation link has expired or has already been used."}, status=status.HTTP_410_GONE)
        return Response({
            "email": invitation.invited_email,
            "staff_number": invitation.staff_number,
            "role": invitation.role,
            "role_display": invitation.get_role_display(),
            "expires_at": invitation.expires_at
        }, status=status.HTTP_200_OK)

    def post(self, request, token):
        """
        Complete account activation: verify NIN from NIMC, set password, create staff account.
        """
        invitation = get_object_or_404(StaffInvitation, token=token)
        if not invitation.is_valid:
            return Response({"error": "This invitation link has expired or has already been used."}, status=status.HTTP_410_GONE)

        nin = request.data.get('nin')
        password = request.data.get('password')

        if not nin or not password:
            return Response({"error": "NIN and password are required to activate your account."}, status=status.HTTP_400_BAD_REQUEST)

        if not nin.isdigit() or len(nin) != 11:
            return Response({"error": "Invalid NIN format."}, status=status.HTTP_400_BAD_REQUEST)

        if len(password) < 6:
            return Response({"error": "Password must be at least 6 characters."}, status=status.HTTP_400_BAD_REQUEST)

        if ElectoralUser.objects.filter(username=nin).exists():
            return Response({"error": "An account with this NIN already exists."}, status=status.HTTP_400_BAD_REQUEST)

        # Verify NIN against NIMC
        try:
            nimc = NIMCRecord.objects.get(nin=nin)
        except NIMCRecord.DoesNotExist:
            return Response({"error": "NIN not found in the National Identity Database. Contact INEC ICT support."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the electoral official account
        user = ElectoralUser.objects.create_user(
            username=nin,
            email=invitation.invited_email,
            password=password,
            full_name=nimc.full_name,
            state=nimc.state,
            lga=nimc.lga,
            role=invitation.role,
            staff_number=invitation.staff_number,
            assigned_polling_unit=invitation.assigned_polling_unit,
            is_verified=True,
            is_staff=True
        )

        # Mark invitation as used
        invitation.is_used = True
        invitation.save()

        # Return token for immediate login
        token_obj, _ = Token.objects.get_or_create(user=user)
        return Response({
            "message": f"Account activated successfully. Welcome, {user.full_name}.",
            "token": token_obj.key,
            "voter": ElectoralUserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class BulkAgentUploadView(views.APIView):
    """
    Party Liaison bulk-uploads a list of NINs to nominate their polling agents.
    The system verifies each NIN against the voter register and upgrades their role to 'agent'
    for the duration of the election period.
    Only 'agent' liaison role or is_staff users can perform this.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff and request.user.role not in ['agent']:
            return Response({"error": "Only authorized party liaisons or ICT Officers can bulk-upload agents."}, status=status.HTTP_403_FORBIDDEN)

        agents_data = request.data.get('agents', [])
        # Expected format: [{"nin": "...", "polling_unit_id": "..."}]

        if not agents_data or not isinstance(agents_data, list):
            return Response({"error": "Provide an 'agents' array with objects containing 'nin' and 'polling_unit_id'."}, status=status.HTTP_400_BAD_REQUEST)

        results = {"upgraded": [], "not_found": [], "already_agent": [], "errors": []}

        for item in agents_data:
            nin = item.get('nin', '').strip()
            pu_id = item.get('polling_unit_id', '').strip()

            if not nin or not nin.isdigit() or len(nin) != 11:
                results["errors"].append({"nin": nin, "reason": "Invalid NIN format"})
                continue

            try:
                user = ElectoralUser.objects.get(username=nin)
                if user.role == 'agent':
                    results["already_agent"].append(nin)
                    continue

                pu = None
                if pu_id:
                    try:
                        pu = PollingUnit.objects.get(id=pu_id)
                    except PollingUnit.DoesNotExist:
                        results["errors"].append({"nin": nin, "reason": f"Polling unit {pu_id} not found"})
                        continue

                user.role = 'agent'
                if pu:
                    user.assigned_polling_unit = pu
                user.save()
                results["upgraded"].append({"nin": nin, "name": user.full_name, "polling_unit": pu_id})

            except ElectoralUser.DoesNotExist:
                results["not_found"].append(nin)

        return Response({
            "message": f"Bulk agent upload complete. {len(results['upgraded'])} upgraded.",
            "results": results
        }, status=status.HTTP_200_OK)


class AccreditationApplicationView(views.APIView):
    """
    Public endpoint for Media houses and Observer organizations to submit
    accreditation applications for review by INEC ICT Officers.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = AccreditationApplicationSerializer(data=request.data)
        if serializer.is_valid():
            app = serializer.save()
            return Response({
                "message": "Your accreditation application has been submitted successfully. You will be contacted at your provided email address once reviewed.",
                "application_id": app.id,
                "organization": app.organization_name,
                "status": app.status
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """Commissioners and Secretaries can view all applications."""
        if not request.user.is_authenticated or request.user.role not in ['commissioner', 'secretary']:
            return Response({"error": "Only INEC Electoral Commissioners or Secretaries can view accreditation applications."}, status=status.HTTP_403_FORBIDDEN)
        apps = AccreditationApplication.objects.all().order_by('-created_at')
        return Response(AccreditationApplicationSerializer(apps, many=True).data, status=status.HTTP_200_OK)


class ReviewAccreditationView(views.APIView):
    """
    INEC Electoral Commissioners review and approve or reject accreditation applications.
    On approval, an invitation email is sent to the contact email with portal access.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if request.user.role not in ['commissioner', 'secretary']:
            return Response({"error": "Only INEC Electoral Commissioners or Secretaries can review applications."}, status=status.HTTP_403_FORBIDDEN)

        app = get_object_or_404(AccreditationApplication, id=pk)
        decision = request.data.get('decision')  # 'approve' or 'reject'
        notes = request.data.get('notes', '')

        if decision not in ['approve', 'reject']:
            return Response({"error": "Decision must be 'approve' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

        app.reviewed_by = request.user
        app.review_notes = notes

        if decision == 'approve':
            app.status = 'approved'
            app.save()

            try:
                # Retrieve the invitation generated by signals
                invitation = StaffInvitation.objects.get(invited_email=app.contact_email)
                frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
                activation_link = f"{frontend_url}/onboard?token={invitation.token}"

                return Response({
                    "message": f"Application APPROVED. Accreditation invitation sent to {app.contact_email}.",
                    "activation_link": activation_link,
                    "staff_number": invitation.staff_number,
                    "role": invitation.role
                }, status=status.HTTP_200_OK)
            except StaffInvitation.DoesNotExist:
                return Response({"error": "Approval saved but invitation record could not be found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            app.status = 'rejected'
            app.save()
            return Response({
                "message": f"Application REJECTED. Reason noted.",
                "notes": notes
            }, status=status.HTTP_200_OK)


# ============================================================
# COMMISSIONER — ELECTION MANAGEMENT VIEWS
# ============================================================

def _require_commissioner(user):
    """Helper: returns an error Response if user is not a commissioner, else None."""
    if user.role != 'commissioner':
        return Response(
            {"error": "Only INEC Electoral Commissioners can perform this action."},
            status=status.HTTP_403_FORBIDDEN
        )
    return None


class ElectionCreateView(views.APIView):
    """
    Commissioners create a new election in 'drafted' state.
    The election is invisible to voters until transitioned to 'upcoming'.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        err = _require_commissioner(request.user)
        if err:
            return err

        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        data['eligible_states'] = [request.user.state]

        serializer = ElectionCreateSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            election = serializer.save()
            return Response({
                "message": f"Election '{election.title}' created in DRAFT status. Add candidates then publish when ready.",
                "election": ElectionSerializer(election, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ElectionManageView(views.APIView):
    """
    Retrieve, update (if draft/upcoming), or delete (if drafted only) an election.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        election = get_object_or_404(Election, id=pk)
        return Response(ElectionSerializer(election, context={'request': request}).data)

    def patch(self, request, pk):
        err = _require_commissioner(request.user)
        if err:
            return err

        election = get_object_or_404(Election, id=pk)
        if election.eligible_states and request.user.state not in election.eligible_states:
            return Response({"error": "You do not have permission to manage elections outside your state."}, status=status.HTTP_403_FORBIDDEN)

        serializer = ElectionUpdateSerializer(election, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Election updated successfully.",
                "election": ElectionSerializer(election, context={'request': request}).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        err = _require_commissioner(request.user)
        if err:
            return err

        election = get_object_or_404(Election, id=pk)
        if election.eligible_states and request.user.state not in election.eligible_states:
            return Response({"error": "You do not have permission to delete elections outside your state."}, status=status.HTTP_403_FORBIDDEN)

        if election.status != 'drafted':
            return Response(
                {"error": f"Only DRAFTED elections can be deleted. This election is '{election.status}'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        title = election.title
        election.delete()
        return Response({"message": f"Election '{title}' has been deleted."}, status=status.HTTP_200_OK)


class ElectionStatusTransitionView(views.APIView):
    """
    Commissioners advance an election through its lifecycle.

    Valid transitions:
      drafted   → upcoming  (publish / announce)
      upcoming  → active    (open polls)
      active    → collation (close polls, begin collation)

    Note: collation → closed is handled separately by multi-sig RO approval.
    """
    permission_classes = [permissions.IsAuthenticated]

    VALID_TRANSITIONS = {
        'drafted':   'upcoming',
        'upcoming':  'active',
        'active':    'collation',
    }

    STATUS_MESSAGES = {
        'upcoming':   "Election published and announced. Voters can now see it in their dashboards.",
        'active':     "Polls are now OPEN. Voters can begin casting their ballots.",
        'collation':  "Polls CLOSED. Collation phase started. Presiding Officers may now upload result sheets.",
    }

    def post(self, request, pk):
        err = _require_commissioner(request.user)
        if err:
            return err

        election = get_object_or_404(Election, id=pk)
        if election.eligible_states and request.user.state not in election.eligible_states:
            return Response({"error": "You do not have permission to advance status for this election outside your state."}, status=status.HTTP_403_FORBIDDEN)
        target = self.VALID_TRANSITIONS.get(election.status)

        if not target:
            return Response(
                {"error": f"Cannot advance election from '{election.status}'. "
                          f"This status has no valid forward transition (or use multi-sig RO closure for collation → closed)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Guard: must have at least 1 candidate before going live
        if target in ['active', 'upcoming'] and election.candidates.count() == 0:
            return Response(
                {"error": "Cannot publish an election with no registered candidates. Add candidates first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        election.status = target
        election.save()

        return Response({
            "message": self.STATUS_MESSAGES[target],
            "election_id": election.id,
            "previous_status": list(self.VALID_TRANSITIONS.keys())[list(self.VALID_TRANSITIONS.values()).index(target)],
            "new_status": target,
        }, status=status.HTTP_200_OK)


class CandidateCreateView(views.APIView):
    """
    Commissioners add candidates to a drafted or upcoming election.
    Candidates cannot be added once an election is active or closed.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        err = _require_commissioner(request.user)
        if err:
            return err

        election = get_object_or_404(Election, id=pk)
        if election.eligible_states and request.user.state not in election.eligible_states:
            return Response({"error": "You do not have permission to add candidates to this election outside your state."}, status=status.HTTP_403_FORBIDDEN)

        if election.status in ['active', 'collation', 'closed']:
            return Response(
                {"error": f"Candidates cannot be added to an election that is '{election.status}'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CandidateCreateSerializer(
            data=request.data,
            context={'election': election, 'request': request}
        )
        if serializer.is_valid():
            candidate = serializer.save()
            return Response({
                "message": f"Candidate '{candidate.name}' ({candidate.party_abbr}) registered for '{election.title}'.",
                "candidate": CandidateSerializer(candidate).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pk):
        election = get_object_or_404(Election, id=pk)
        candidates = election.candidates.all()
        return Response(CandidateSerializer(candidates, many=True).data)


class CandidateDeleteView(views.APIView):
    """
    Commissioners can remove a candidate from a drafted/upcoming election.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, candidate_id):
        err = _require_commissioner(request.user)
        if err:
            return err

        election = get_object_or_404(Election, id=pk)
        candidate = get_object_or_404(Candidate, id=candidate_id, election=election)
        if election.eligible_states and request.user.state not in election.eligible_states:
            return Response({"error": "You do not have permission to remove candidates from this election outside your state."}, status=status.HTTP_403_FORBIDDEN)

        if election.status in ['active', 'collation', 'closed']:
            return Response(
                {"error": "Cannot remove candidates from an active or closed election."},
                status=status.HTTP_400_BAD_REQUEST
            )

        name = candidate.name
        candidate.delete()
        return Response({"message": f"Candidate '{name}' removed from '{election.title}'."}, status=status.HTTP_200_OK)


class CommissionerElectionListView(views.APIView):
    """
    Returns ALL elections (including drafts) visible only to commissioners, secretaries, and auditors.
    Regular voters only see upcoming/active/closed elections via ElectionListView.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['commissioner', 'auditor', 'secretary']:
            return Response({"error": "Access restricted."}, status=status.HTTP_403_FORBIDDEN)

        elections = Election.objects.prefetch_related('candidates', 'closure_approvals').all()
        
        # Filter by state for commissioner
        if request.user.role == 'commissioner':
            filtered_elections = []
            for e in elections:
                if not e.eligible_states or request.user.state in e.eligible_states:
                    filtered_elections.append(e)
            elections = filtered_elections

        return Response(
            ElectionSerializer(elections, many=True, context={'request': request}).data
        )


class SecretaryMetricsView(views.APIView):
    """
    Exposes metrics for the INEC Secretary Dashboard.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != 'secretary':
            return Response({"error": "Access restricted to INEC Secretary only."}, status=status.HTTP_403_FORBIDDEN)

        total_voters = ElectoralUser.objects.filter(role='voter').count()
        
        from django.db.models import Sum
        total_votes_cast = ResultSheet.objects.aggregate(total=Sum('total_votes_cast'))['total'] or 0
        
        total_polling_units = PollingUnit.objects.count()
        total_elections = Election.objects.count()
        
        total_staff = ElectoralUser.objects.exclude(role__in=['voter', 'prospective']).count()
        total_invitations = StaffInvitation.objects.count()
        total_accreditations = AccreditationApplication.objects.count()

        return Response({
            "total_voters": total_voters,
            "total_votes_cast": total_votes_cast,
            "total_polling_units": total_polling_units,
            "total_elections": total_elections,
            "total_staff": total_staff,
            "total_invitations": total_invitations,
            "total_accreditations": total_accreditations
        }, status=status.HTTP_200_OK)
