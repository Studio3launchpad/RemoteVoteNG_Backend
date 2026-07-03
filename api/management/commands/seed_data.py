from django.core.management.base import BaseCommand
from api.models import NIMCRecord, Election, Candidate, PollingUnit, ElectoralUser

class Command(BaseCommand):
    help = 'Seeds the database with mock NIMC records, polling units, elections, candidates, and staff users.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding NIMC Records...')
        
        # Mock NIMC Records
        nimc_records = [
            { 'nin': '11111111111', 'full_name': 'Kelvin Adebayo', 'state': 'Lagos', 'lga': 'Ikeja' },
            { 'nin': '22222222222', 'full_name': 'Adaeze Nwosu', 'state': 'Enugu', 'lga': 'Enugu North' },
            { 'nin': '33333333333', 'full_name': 'Musa Abdullahi', 'state': 'Kano', 'lga': 'Fagge' },
            { 'nin': '44444444444', 'full_name': 'Chinedu Okonkwo', 'state': 'Anambra', 'lga': 'Onitsha South' },
            { 'nin': '55555555555', 'full_name': 'Amina Bello', 'state': 'Kaduna', 'lga': 'Kaduna North' },
            { 'nin': '12345678901', 'full_name': 'Peter Ojo', 'state': 'Oyo', 'lga': 'Ibadan North' },
            { 'nin': '98765432109', 'full_name': 'Chioma Egwu', 'state': 'Rivers', 'lga': 'Port Harcourt' }
        ]

        for record in nimc_records:
            obj, created = NIMCRecord.objects.get_or_create(
                nin=record['nin'],
                defaults={
                    'full_name': record['full_name'],
                    'state': record['state'],
                    'lga': record['lga'],
                    'biometric_hash': 'mock_biometric_hash_xyz_123'
                }
            )
            if created:
                self.stdout.write(f'  Created NIMC record for {record["full_name"]}')
            else:
                self.stdout.write(f'  NIMC record for {record["full_name"]} already exists')

        self.stdout.write('Seeding Polling Units...')
        
        # Polling Units
        polling_units = [
            { 'id': 'PU-24-05-11', 'name': 'Ikeja PU 1 - Alausa Primary School', 'ward': 'Alausa', 'lga': 'Ikeja', 'state': 'Lagos', 'registered_voters_count': 1250 },
            { 'id': 'PU-24-05-12', 'name': 'Ikeja PU 2 - Police College Ground', 'ward': 'Gra Ikeja', 'lga': 'Ikeja', 'state': 'Lagos', 'registered_voters_count': 1400 },
            { 'id': 'PU-14-02-01', 'name': 'Enugu North PU 3 - Central School Ward 1', 'ward': 'Ward 1', 'lga': 'Enugu North', 'state': 'Enugu', 'registered_voters_count': 900 }
        ]

        for pu in polling_units:
            obj, created = PollingUnit.objects.get_or_create(
                id=pu['id'],
                defaults={
                    'name': pu['name'],
                    'ward': pu['ward'],
                    'lga': pu['lga'],
                    'state': pu['state'],
                    'registered_voters_count': pu['registered_voters_count']
                }
            )
            if created:
                self.stdout.write(f'  Created polling unit: {pu["name"]}')

        self.stdout.write('Seeding Elections...')
        
        # Elections
        elections = [
            { 'id': 'presidential-2027', 'title': 'Presidential Election', 'date': '2027-02-25', 'status': 'active', 'election_type': 'presidential' },
            { 'id': 'senate-2027', 'title': 'National Assembly — Senate', 'date': '2027-02-25', 'status': 'active', 'election_type': 'senatorial' },
            { 'id': 'house-2027', 'title': 'House of Representatives', 'date': '2027-02-25', 'status': 'upcoming', 'election_type': 'house_reps' },
            { 'id': 'governorship-2027', 'title': 'Governorship Election', 'date': '2027-03-11', 'status': 'upcoming', 'election_type': 'gubernatorial' }
        ]

        for el in elections:
            obj, created = Election.objects.get_or_create(
                id=el['id'],
                defaults={
                    'title': el['title'],
                    'date': el['date'],
                    'status': el['status'],
                    'election_type': el.get('election_type', 'presidential'),
                }
            )
            if created:
                self.stdout.write(f'  Created election: {el["title"]}')
            else:
                obj.status = el['status']
                obj.election_type = el.get('election_type', obj.election_type)
                obj.save()

        self.stdout.write('Seeding Candidates...')

        # Candidates
        candidates_data = {
            'presidential-2027': [
                { 'id': 'c1', 'name': 'Adaeze Nwosu', 'party': 'Green Alliance Party', 'party_abbr': 'GAP', 'color': '#2e7d32', 'manifesto': 'Renewable energy, youth employment, and transparent governance.', 'running_mate': 'Yusuf Bello' },
                { 'id': 'c2', 'name': 'Musa Abdullahi', 'party': 'Unity Progressive Movement', 'party_abbr': 'UPM', 'color': '#1565c0', 'manifesto': 'Security-first agenda, federal restructuring, digital economy.', 'running_mate': 'Ifeoma Eze' },
                { 'id': 'c3', 'name': 'Chinedu Okonkwo', 'party': "People's Reform Congress", 'party_abbr': 'PRC', 'color': '#c62828', 'manifesto': 'Free healthcare, agricultural revolution, anti-corruption courts.', 'running_mate': 'Amina Sani' }
            ],
            'senate-2027': [
                { 'id': 's1', 'name': 'Ngozi Okafor', 'party': 'Green Alliance Party', 'party_abbr': 'GAP', 'color': '#2e7d32', 'manifesto': 'Constituency projects, healthcare access.' },
                { 'id': 's2', 'name': 'Ibrahim Danjuma', 'party': 'Unity Progressive Movement', 'party_abbr': 'UPM', 'color': '#1565c0', 'manifesto': 'Infrastructure, security funding.' }
            ]
        }

        for election_id, candidates in candidates_data.items():
            election = Election.objects.get(id=election_id)
            for cand in candidates:
                obj, created = Candidate.objects.get_or_create(
                    id=cand['id'],
                    defaults={
                        'election': election,
                        'name': cand['name'],
                        'party': cand['party'],
                        'party_abbr': cand['party_abbr'],
                        'color': cand['color'],
                        'manifesto': cand['manifesto'],
                        'running_mate': cand.get('running_mate', ''),
                        'votes_count': 14000
                    }
                )
                if created:
                    self.stdout.write(f'  Created candidate: {cand["name"]} for {election_id}')

        self.stdout.write('Seeding Staff Users (RBAC)...')

        # Staff Users details
        staff_data = [
            # --- INEC HQ ---
            { 'username': '90000000000', 'staff_number': 'STAFF-COMM', 'full_name': 'Chief Electoral Commissioner', 'email': 'commissioner@remotevote.org', 'role': 'commissioner', 'pu_id': None, 'state': 'Lagos', 'superuser': False },
            { 'username': '90000000008', 'staff_number': 'STAFF-SECRETARY', 'full_name': 'INEC Secretary', 'email': 'secretary@remotevote.org', 'role': 'secretary', 'pu_id': None, 'superuser': False },
            # --- Field Staff ---
            { 'username': '90000000001', 'staff_number': 'STAFF-PO', 'full_name': 'Babatunde Bello', 'email': 'po@remotevote.org', 'role': 'po', 'pu_id': 'PU-24-05-11', 'superuser': False },
            { 'username': '90000000002', 'staff_number': 'STAFF-CO', 'full_name': 'Funmi Coker', 'email': 'co@remotevote.org', 'role': 'co', 'pu_id': None, 'superuser': False },
            { 'username': '90000000003', 'staff_number': 'STAFF-RO', 'full_name': 'Professor Ibrahim Agboola', 'email': 'ro@remotevote.org', 'role': 'ro', 'pu_id': None, 'superuser': True },
            { 'username': '90000000004', 'staff_number': 'STAFF-AGENT', 'full_name': 'Chidi Nwankwo', 'email': 'agent@remotevote.org', 'role': 'agent', 'pu_id': 'PU-24-05-11', 'superuser': False },
            { 'username': '90000000005', 'staff_number': 'STAFF-OBSERVER', 'full_name': 'Sarah Jenkins', 'email': 'observer@remotevote.org', 'role': 'observer', 'pu_id': None, 'superuser': False },
            { 'username': '90000000006', 'staff_number': 'STAFF-MEDIA', 'full_name': 'Kelvin Cole', 'email': 'media@remotevote.org', 'role': 'media', 'pu_id': None, 'superuser': False },
            { 'username': '90000000007', 'staff_number': 'STAFF-AUDITOR', 'full_name': 'Damilola Craig', 'email': 'auditor@remotevote.org', 'role': 'auditor', 'pu_id': None, 'superuser': True },
        ]

        for s in staff_data:
            pu = PollingUnit.objects.get(id=s['pu_id']) if s['pu_id'] else None

            user_exists = ElectoralUser.objects.filter(username=s['username']).exists()
            if not user_exists:
                user = ElectoralUser.objects.create_user(
                    username=s['username'],
                    staff_number=s['staff_number'],
                    email=s['email'],
                    password='password123',
                    full_name=s['full_name'],
                    role=s['role'],
                    assigned_polling_unit=pu,
                    state=s.get('state', ''),
                    is_verified=True,
                    is_staff=True
                )
                if s.get('superuser'):
                    user.is_superuser = True
                    user.save()
                self.stdout.write(f'  Created {s["role"].upper()} user: {s["full_name"]} | Login: {s["staff_number"]} | Password: password123')
            else:
                user = ElectoralUser.objects.get(username=s['username'])
                user.staff_number = s['staff_number']
                user.role = s['role']
                user.assigned_polling_unit = pu
                user.state = s.get('state', user.state)
                user.is_verified = True
                user.is_staff = True
                if s.get('superuser'):
                    user.is_superuser = True
                user.save()
                self.stdout.write(f'  Updated {s["role"].upper()} user: {s["full_name"]}')

        # Assign PO and CO to Polling Units
        self.stdout.write('Assigning Presiding and Collation Officers to Polling Units...')
        try:
            pu_alausa = PollingUnit.objects.get(id='PU-24-05-11')
            po_user = ElectoralUser.objects.get(staff_number='STAFF-PO')
            co_user = ElectoralUser.objects.get(staff_number='STAFF-CO')
            pu_alausa.presiding_officer = po_user
            pu_alausa.collation_officer = co_user
            pu_alausa.save()
            self.stdout.write('  Assigned Babatunde Bello (PO) and Funmi Coker (CO) to PU-24-05-11.')
        except Exception as e:
            self.stdout.write(f'  Error assigning PU officers: {str(e)}')

        self.stdout.write(self.style.SUCCESS('Successfully seeded database with roles.'))
