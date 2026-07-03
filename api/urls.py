from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),
    path('auth/profile/', views.ProfileView.as_view(), name='profile'),

    # Elections — Public / Voter
    path('elections/', views.ElectionListView.as_view(), name='election-list'),
    path('elections/<str:pk>/', views.ElectionDetailView.as_view(), name='election-detail'),
    path('elections/<str:pk>/closure-approvals/', views.ElectionClosureApprovalsView.as_view(), name='closure-approvals'),
    path('elections/<str:pk>/approve-closure/', views.ApproveElectionClosureView.as_view(), name='approve-closure'),
    path('vote/', views.CastVoteView.as_view(), name='cast-vote'),

    # Commissioner — Election Management
    path('commissioner/elections/', views.CommissionerElectionListView.as_view(), name='commissioner-election-list'),
    path('commissioner/elections/create/', views.ElectionCreateView.as_view(), name='election-create'),
    path('commissioner/elections/<str:pk>/', views.ElectionManageView.as_view(), name='election-manage'),
    path('commissioner/elections/<str:pk>/advance/', views.ElectionStatusTransitionView.as_view(), name='election-advance'),
    path('commissioner/elections/<str:pk>/candidates/', views.CandidateCreateView.as_view(), name='candidate-create'),
    path('commissioner/elections/<str:pk>/candidates/<str:candidate_id>/', views.CandidateDeleteView.as_view(), name='candidate-delete'),

    # Staff Operational Endpoints
    path('results-sheets/', views.ResultSheetListCreateView.as_view(), name='results-sheets'),
    path('results-sheets/<uuid:pk>/verify/', views.ResultSheetVerifyView.as_view(), name='results-sheets-verify'),
    path('disputes/', views.DisputeLogListCreateView.as_view(), name='disputes'),
    path('disputes/<int:pk>/resolve/', views.DisputeResolveView.as_view(), name='disputes-resolve'),
    path('audit-logs/', views.AuditLogListView.as_view(), name='audit-logs'),
    path('polling-units/', views.PollingUnitListCreateView.as_view(), name='polling-units'),
    path('polling-units/<str:pk>/', views.PollingUnitManageView.as_view(), name='polling-units-manage'),
    path('nimc-records/', views.NIMCRecordListCreateView.as_view(), name='nimc-records'),
    path('nimc-records/<int:pk>/', views.NIMCRecordManageView.as_view(), name='nimc-records-manage'),

    # Onboarding Flows
    path('onboarding/invite/', views.SendStaffInvitationView.as_view(), name='send-invitation'),
    path('onboarding/invite/<int:pk>/resend/', views.ResendStaffInvitationView.as_view(), name='resend-invitation'),
    path('onboarding/invitations/', views.StaffInvitationListView.as_view(), name='invitation-list'),
    path('onboarding/accept/<str:token>/', views.AcceptStaffInvitationView.as_view(), name='accept-invitation'),
    path('onboarding/bulk-agents/', views.BulkAgentUploadView.as_view(), name='bulk-agents'),
    path('onboarding/accreditation/', views.AccreditationApplicationView.as_view(), name='accreditation'),
    path('onboarding/accreditation/<int:pk>/review/', views.ReviewAccreditationView.as_view(), name='review-accreditation'),
    
    # INEC Secretary Metrics
    path('secretary/metrics/', views.SecretaryMetricsView.as_view(), name='secretary-metrics'),
]


