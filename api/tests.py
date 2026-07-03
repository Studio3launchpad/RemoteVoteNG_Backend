from django.test import TestCase, Client
from django.contrib.auth import authenticate
from django.urls import reverse
from api.models import ElectoralUser, NIMCRecord, PollingUnit, Election, Candidate, AuditLog
from api.middleware import _thread_locals


class EVotingAuthenticationTests(TestCase):
    def setUp(self):
        # Create NIMC record
        NIMCRecord.objects.create(
            nin='11111111111',
            full_name='Kelvin Adebayo',
            state='Lagos',
            lga='Ikeja',
            biometric_hash='hash123'
        )
        
        # Create Voter User
        self.voter = ElectoralUser.objects.create_user(
            username='11111111111',
            email='kelvin@adebayo.org',
            password='password123',
            full_name='Kelvin Adebayo',
            state='Lagos',
            lga='Ikeja',
            role='voter',
            is_verified=True
        )

        # Create Staff User
        self.staff = ElectoralUser.objects.create_user(
            username='90000000001',
            staff_number='STAFF-PO',
            email='po@remotevote.org',
            password='password123',
            full_name='Babatunde Bello',
            role='po',
            is_verified=True,
            is_staff=True
        )

    def test_authenticate_by_nin(self):
        # Test authenticating voter by NIN
        user = authenticate(username='11111111111', password='password123')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, '11111111111')
        self.assertEqual(user.role, 'voter')

    def test_authenticate_by_staff_number(self):
        # Test authenticating staff by staff_number
        user = authenticate(username='STAFF-PO', password='password123')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, '90000000001')
        self.assertEqual(user.staff_number, 'STAFF-PO')
        self.assertEqual(user.role, 'po')

    def test_authenticate_invalid_password(self):
        user = authenticate(username='STAFF-PO', password='wrongpassword')
        self.assertIsNone(user)


class AuditLogSignalTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Clean thread locals to avoid side effects
        _thread_locals.user = None
        _thread_locals.ip = None
        
        # Create test voter user
        self.user = ElectoralUser.objects.create_user(
            username='22222222222',
            email='ada@nwosu.org',
            password='password123',
            full_name='Ada Nwosu',
            state='Enugu',
            lga='Enugu North',
            role='voter',
            is_verified=True
        )
        
        # Setup clean election
        self.election = Election.objects.create(
            id='test-election',
            title='Test Election',
            date='2027-02-25',
            status='active'
        )

    def test_crud_audit_logs_created(self):
        # 1. Test CREATE signal logging
        # We manually simulate having a user in thread-local storage (like middleware does)
        _thread_locals.user = self.user
        _thread_locals.ip = '192.168.1.1'

        candidate = Candidate.objects.create(
            id='tc1',
            election=self.election,
            name='Test Candidate',
            party='Test Party',
            party_abbr='TP',
            color='#ffffff',
            manifesto='A testing manifesto'
        )

        # Retrieve audit logs
        logs = AuditLog.objects.filter(model_name='Candidate')
        self.assertEqual(logs.count(), 1)
        create_log = logs.first()
        self.assertEqual(create_log.action, 'CREATE')
        self.assertEqual(create_log.user, self.user)
        self.assertEqual(create_log.ip_address, '192.168.1.1')
        self.assertEqual(create_log.object_id, 'tc1')

        # 2. Test UPDATE signal logging
        candidate.name = 'Updated Test Candidate'
        candidate.save()

        logs = AuditLog.objects.filter(model_name='Candidate').order_back = AuditLog.objects.filter(model_name='Candidate').order_by('-timestamp')
        self.assertEqual(logs.count(), 2)
        update_log = logs.first()
        self.assertEqual(update_log.action, 'UPDATE')
        self.assertEqual(update_log.user, self.user)

        # 3. Test DELETE signal logging
        candidate.delete()
        logs = AuditLog.objects.filter(model_name='Candidate').order_by('-timestamp')
        self.assertEqual(logs.count(), 3)
        delete_log = logs.first()
        self.assertEqual(delete_log.action, 'DELETE')
        self.assertEqual(delete_log.user, self.user)


class StaffInvitationTests(TestCase):
    def setUp(self):
        # Create Commissioner User
        self.comm = ElectoralUser.objects.create_user(
            username='STAFF-COMM',
            staff_number='STAFF-COMM',
            email='comm@remotevote.org',
            password='password123',
            full_name='Chief Electoral Commissioner',
            role='commissioner',
            is_verified=True,
            is_staff=True
        )
        from rest_framework.authtoken.models import Token
        self.token, _ = Token.objects.get_or_create(user=self.comm)
        self.client = Client()

    def test_resend_invitation(self):
        # Create an invitation
        from api.models import StaffInvitation
        invitation = StaffInvitation.create_invitation(
            email='po_test@remotevote.org',
            staff_number='STAFF-PO-999999',
            role='po',
            invited_by=self.comm
        )

        response = self.client.post(
            f'/api/onboarding/invite/{invitation.id}/resend/',
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {self.token.key}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invitation email resent successfully", response.json()['message'])


class AdvancedElectoralControlTests(TestCase):
    def setUp(self):
        from rest_framework.authtoken.models import Token
        # Create Lagos Commissioner
        self.comm_lagos = ElectoralUser.objects.create_user(
            username='11111111111',
            staff_number='STAFF-COMM-LOS',
            email='comm_los@remotevote.org',
            password='password123',
            full_name='Lagos Commissioner',
            role='commissioner',
            state='Lagos',
            is_verified=True,
            is_staff=True
        )
        self.token_lagos, _ = Token.objects.get_or_create(user=self.comm_lagos)

        # Create Kano Commissioner
        self.comm_kano = ElectoralUser.objects.create_user(
            username='22222222222',
            staff_number='STAFF-COMM-KAN',
            email='comm_kan@remotevote.org',
            password='password123',
            full_name='Kano Commissioner',
            role='commissioner',
            state='Kano',
            is_verified=True,
            is_staff=True
        )
        self.token_kano, _ = Token.objects.get_or_create(user=self.comm_kano)

        # Create INEC Secretary
        self.secretary = ElectoralUser.objects.create_user(
            username='33333333333',
            staff_number='STAFF-SEC-01',
            email='secretary@remotevote.org',
            password='password123',
            full_name='INEC Secretary',
            role='secretary',
            is_verified=True,
            is_staff=True
        )
        self.token_sec, _ = Token.objects.get_or_create(user=self.secretary)

        # Create Polling Units
        from api.models import PollingUnit
        self.pu_lagos = PollingUnit.objects.create(id='PU-LOS-01', name='Lagos PU', ward='Ward A', lga='Ikeja', state='Lagos')
        self.pu_kano = PollingUnit.objects.create(id='PU-KAN-01', name='Kano PU', ward='Ward B', lga='Nasarawa', state='Kano')

        # Create Election
        from api.models import Election
        from django.utils import timezone
        import datetime
        self.election = Election.objects.create(
            id='election-1',
            title='Presidential Election',
            election_type='presidential',
            date=datetime.date.today(),
            status='active'
        )

        self.client = Client()

    def test_commissioner_state_isolation(self):
        # Lagos commissioner can see Lagos PU
        response = self.client.get(
            '/api/polling-units/',
            HTTP_AUTHORIZATION=f'Token {self.token_lagos.key}'
        )
        self.assertEqual(response.status_code, 200)
        p_units = response.json()
        self.assertEqual(len(p_units), 1)
        self.assertEqual(p_units[0]['id'], 'PU-LOS-01')

        # Lagos commissioner CANNOT create Kano PU
        response = self.client.post(
            '/api/polling-units/',
            data={
                "id": "PU-KAN-02",
                "name": "Kano PU 2",
                "ward": "Ward B",
                "lga": "Nasarawa",
                "state": "Kano"
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {self.token_lagos.key}'
        )
        self.assertEqual(response.status_code, 403)

        # Lagos commissioner CANNOT delete Kano PU (returns 404 as it is not in Lagos queryset)
        response = self.client.delete(
            f'/api/polling-units/{self.pu_kano.id}/',
            HTTP_AUTHORIZATION=f'Token {self.token_lagos.key}'
        )
        self.assertEqual(response.status_code, 404)

    def test_votes_preservation_on_polling_unit_delete(self):
        # Create a ResultSheet for Lagos PU
        from api.models import ResultSheet
        sheet = ResultSheet.objects.create(
            election=self.election,
            polling_unit=self.pu_lagos,
            presiding_officer=self.comm_lagos,
            scanned_form_url='http://example.com/form.pdf',
            accredited_voters=100,
            total_votes_cast=90,
            po_digital_signature='sig-1'
        )

        # Delete Polling Unit
        self.pu_lagos.delete()

        # Check that ResultSheet still exists but polling_unit is NULL
        sheet.refresh_from_db()
        self.assertIsNone(sheet.polling_unit)

    def test_secretary_permissions_and_metrics(self):
        # Get metrics
        response = self.client.get(
            '/api/secretary/metrics/',
            HTTP_AUTHORIZATION=f'Token {self.token_sec.key}'
        )
        self.assertEqual(response.status_code, 200)
        metrics = response.json()
        self.assertEqual(metrics['total_polling_units'], 2)
        self.assertEqual(metrics['total_elections'], 1)

        # Secretary CANNOT create a polling unit
        response = self.client.post(
            '/api/polling-units/',
            data={
                "id": "PU-LOS-02",
                "name": "Lagos PU 2",
                "ward": "Ward A",
                "lga": "Ikeja",
                "state": "Lagos"
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {self.token_sec.key}'
        )
        self.assertEqual(response.status_code, 403)

        # Secretary CAN invite staff (e.g. Presiding Officer)
        response = self.client.post(
            '/api/onboarding/invite/',
            data={
                "email": "po_sec@remotevote.org",
                "role": "po"
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {self.token_sec.key}'
        )
        self.assertEqual(response.status_code, 201)


