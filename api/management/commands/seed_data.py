import random
import string
import uuid
import secrets
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from api.models import (
    NIMCRecord, PollingUnit, ElectoralUser, Election,
    Candidate, ResultSheet, DisputeLog, ElectionParticipation,
    StaffInvitation, AccreditationApplication, VoterRegistrationRecord
)

# ─── Nigerian Data Pools ──────────────────────────────────────────────────────

NIGERIAN_STATES = [
    'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue',
    'Borno', 'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu',
    'FCT', 'Gombe', 'Imo', 'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi',
    'Kogi', 'Kwara', 'Lagos', 'Nasarawa', 'Niger', 'Ogun', 'Ondo', 'Osun',
    'Oyo', 'Plateau', 'Rivers', 'Sokoto', 'Taraba', 'Yobe', 'Zamfara',
]

STATE_LGAS = {
    'Lagos':     ['Ikeja', 'Surulere', 'Eti-Osa', 'Agege', 'Alimosho', 'Mushin', 'Kosofe', 'Shomolu'],
    'Kano':      ['Fagge', 'Gwale', 'Kano Municipal', 'Nassarawa', 'Tarauni', 'Ungogo', 'Dala'],
    'Rivers':    ['Port Harcourt', 'Obio-Akpor', 'Eleme', 'Ikwerre', 'Emohua', 'Oyigbo'],
    'Oyo':       ['Ibadan North', 'Ibadan South', 'Akinyele', 'Egbeda', 'Lagelu', 'Oluyole'],
    'Kaduna':    ['Kaduna North', 'Kaduna South', 'Chikun', 'Igabi', 'Zaria', 'Sabon Gari'],
    'Enugu':     ['Enugu North', 'Enugu South', 'Igbo-Eze North', 'Nkanu East', 'Udi'],
    'Anambra':   ['Onitsha North', 'Onitsha South', 'Awka North', 'Awka South', 'Nnewi North'],
    'FCT':       ['Abuja Municipal', 'Bwari', 'Gwagwalada', 'Kuje', 'Lugbe', 'Kwali'],
    'Delta':     ['Warri North', 'Warri South', 'Oshimili North', 'Asaba', 'Ethiope East'],
    'Imo':       ['Owerri North', 'Owerri West', 'Owerri Municipal', 'Mbaitoli', 'Orlu'],
    'Borno':     ['Maiduguri', 'Jere', 'Konduga', 'Kaga', 'Kukawa'],
    'Bauchi':    ['Bauchi', 'Dass', 'Ganjuwa', 'Kirfi', 'Ningi'],
    'Sokoto':    ['Sokoto North', 'Sokoto South', 'Bodinga', 'Dange Shuni'],
    'Adamawa':   ['Yola North', 'Yola South', 'Gombi', 'Girei', 'Hong'],
}
DEFAULT_LGA = ['Central', 'North', 'South', 'East', 'West']

STATE_CODES = {
    'Abia': 'ABI', 'Adamawa': 'ADA', 'Akwa Ibom': 'AKW', 'Anambra': 'ANA',
    'Bauchi': 'BAU', 'Bayelsa': 'BAY', 'Benue': 'BEN', 'Borno': 'BOR',
    'Cross River': 'CRO', 'Delta': 'DEL', 'Ebonyi': 'EBO', 'Edo': 'EDO',
    'Ekiti': 'EKI', 'Enugu': 'ENU', 'FCT': 'FCT', 'Gombe': 'GOM',
    'Imo': 'IMO', 'Jigawa': 'JIG', 'Kaduna': 'KAD', 'Kano': 'KAN',
    'Katsina': 'KAT', 'Kebbi': 'KEB', 'Kogi': 'KOG', 'Kwara': 'KWA',
    'Lagos': 'LAG', 'Nasarawa': 'NAS', 'Niger': 'NIG', 'Ogun': 'OGU',
    'Ondo': 'OND', 'Osun': 'OSU', 'Oyo': 'OYO', 'Plateau': 'PLA',
    'Rivers': 'RIV', 'Sokoto': 'SOK', 'Taraba': 'TAR', 'Yobe': 'YOB',
    'Zamfara': 'ZAM',
}

FIRST_NAMES = [
    'Aminu', 'Fatima', 'Chukwuemeka', 'Ngozi', 'Yusuf', 'Adesola', 'Ibraheem',
    'Chidinma', 'Obinna', 'Hauwa', 'Babatunde', 'Adaeze', 'Musa', 'Ifeoma',
    'Emeka', 'Amina', 'Tunde', 'Chinwe', 'Aliyu', 'Blessing', 'Kelechi',
    'Halima', 'Oluwaseun', 'Uchenna', 'Abdullahi', 'Chiamaka', 'Segun',
    'Nkechi', 'Suleiman', 'Adaora', 'Taiwo', 'Chisom', 'Garba', 'Omotola',
    'Chidi', 'Zainab', 'Rotimi', 'Ebele', 'Bello', 'Adunola',
    'Salamatu', 'Femi', 'Uche', 'Yakubu', 'Funmi', 'Nnamdi', 'Rabi',
    'Tobi', 'Chioma', 'Ibrahim', 'Adeola', 'Gbenga', 'Stella', 'Ahmed',
    'Perpetua', 'Kayode', 'Vivian', 'Lawan', 'Nneka', 'Dauda', 'Oluchi',
]
LAST_NAMES = [
    'Adebayo', 'Nwosu', 'Abdullahi', 'Okonkwo', 'Bello', 'Adesanya', 'Eze',
    'Okafor', 'Aliyu', 'Adeyemi', 'Musa', 'Chukwu', 'Garba', 'Okeke',
    'Danjuma', 'Ibe', 'Usman', 'Egwu', 'Obi', 'Sani', 'Ogundele', 'Anyanwu',
    'Lawan', 'Okoye', 'Shehu', 'Obiora', 'Mohammed', 'Ikenna', 'Dangote',
    'Obasi', 'Tanko', 'Agu', 'Gana', 'Ekwueme', 'Nwachukwu', 'Issa',
    'Adeleke', 'Onuoha', 'Bukar', 'Uzor', 'Idowu', 'Amadi', 'Makarfi',
    'Nweze', 'Abubakar', 'Chima', 'Bala', 'Iwu', 'Haruna', 'Ogbu',
]

PARTIES = [
    ('All Progressives Congress', 'APC', '#2e7d32'),
    ('Peoples Democratic Party', 'PDP', '#c62828'),
    ('Labour Party', 'LP', '#e65100'),
    ('New Nigeria Peoples Party', 'NNPP', '#6a1b9a'),
    ('All Progressives Grand Alliance', 'APGA', '#1565c0'),
    ('Social Democratic Party', 'SDP', '#00838f'),
    ('Accord', 'ACC', '#4a148c'),
]

ELECTION_CONFIGS = [
    {'id': 'presidential-2027', 'title': '2027 Presidential Election', 'type': 'presidential', 'status': 'active', 'date': str(date.today()), 'eligible_states': []},
    {'id': 'senate-2027', 'title': '2027 National Assembly — Senate', 'type': 'senatorial', 'status': 'active', 'date': str(date.today()), 'eligible_states': []},
    {'id': 'house-reps-2027', 'title': '2027 House of Representatives', 'type': 'house_reps', 'status': 'active', 'date': str(date.today()), 'eligible_states': []},
    {'id': 'governorship-lagos-2027', 'title': '2027 Lagos Governorship', 'type': 'gubernatorial', 'status': 'active', 'date': str(date.today()), 'eligible_states': ['Lagos']},
    {'id': 'governorship-kano-2027', 'title': '2027 Kano Governorship', 'type': 'gubernatorial', 'status': 'active', 'date': str(date.today()), 'eligible_states': ['Kano']},
    {'id': 'assembly-oyo-2027', 'title': '2027 Oyo House of Assembly', 'type': 'state_assembly', 'status': 'active', 'date': str(date.today()), 'eligible_states': ['Oyo']},
]

FACILITY_TYPES = [
    'Primary School', 'Community Hall', 'Town Hall', 'Civic Centre',
    'Secondary School', 'Market Square', 'Ward Office', 'Health Centre',
    'Church Hall', 'Mosque Grounds', 'Police Station Grounds', 'Sports Centre',
]

MEDIA_ORGS = [
    'Channels Television', 'NTA Lagos', 'TVC News', 'AIT', 'Arise News',
    'Punch Newspapers', 'The Guardian Nigeria', 'Daily Trust', 'Sun Publishing',
    'Sahara Reporters', 'Premium Times', 'Vanguard Media',
]

OBSERVER_ORGS = [
    'Transition Monitoring Group', 'Civil Society Network', 'Yiaga Africa',
    'African Union Observer Mission', 'ECOWAS Observer Group', 'EU Election Observation',
    'Carter Center Nigeria', 'DFID Nigeria Observers', 'Commonwealth Observers',
    'Joint Election Monitoring Group', 'Nigerian Women Trust Fund',
]

# 25 hand-crafted VRN records with matching real-looking NIMs
# These are used for testing; VRN + NIN pairs that a voter can use on signup
FIXED_VRN_RECORDS = [
    {'vrn': 'LAG12345678AB', 'nin': '11111111111', 'full_name': 'Kelvin Adebayo',       'dob': '1990-04-15', 'gender': 'M', 'state': 'Lagos',     'lga': 'Ikeja',          'ward': 'Ward 3'},
    {'vrn': 'ENU22345678CD', 'nin': '22222222222', 'full_name': 'Adaeze Nwosu',         'dob': '1988-07-22', 'gender': 'F', 'state': 'Enugu',     'lga': 'Enugu North',    'ward': 'Ward 1'},
    {'vrn': 'KAN33345678EF', 'nin': '33333333333', 'full_name': 'Musa Abdullahi',       'dob': '1995-11-03', 'gender': 'M', 'state': 'Kano',      'lga': 'Fagge',          'ward': 'Ward 5'},
    {'vrn': 'ANA44445678GH', 'nin': '44444444444', 'full_name': 'Chinedu Okonkwo',     'dob': '1992-02-28', 'gender': 'M', 'state': 'Anambra',   'lga': 'Onitsha South',  'ward': 'Ward 2'},
    {'vrn': 'KAD55545678IJ', 'nin': '55555555555', 'full_name': 'Amina Bello',         'dob': '1997-06-10', 'gender': 'F', 'state': 'Kaduna',    'lga': 'Kaduna North',   'ward': 'Ward 7'},
    {'vrn': 'OYO12365678KL', 'nin': '12345678901', 'full_name': 'Peter Ojo',           'dob': '1985-09-17', 'gender': 'M', 'state': 'Oyo',       'lga': 'Ibadan North',   'ward': 'Ward 4'},
    {'vrn': 'RIV98735678MN', 'nin': '98765432109', 'full_name': 'Chioma Egwu',         'dob': '1993-12-01', 'gender': 'F', 'state': 'Rivers',    'lga': 'Port Harcourt',  'ward': 'Ward 9'},
    {'vrn': 'FCT10235678OP', 'nin': '10234567891', 'full_name': 'Emeka Okafor',        'dob': '1991-03-25', 'gender': 'M', 'state': 'FCT',       'lga': 'Abuja Municipal','ward': 'Ward 1'},
    {'vrn': 'LAG20235678QR', 'nin': '20234567891', 'full_name': 'Funmi Adeyemi',       'dob': '1994-08-14', 'gender': 'F', 'state': 'Lagos',     'lga': 'Surulere',       'ward': 'Ward 6'},
    {'vrn': 'DEL30235678ST', 'nin': '30234567891', 'full_name': 'Bright Obi',          'dob': '1989-01-30', 'gender': 'M', 'state': 'Delta',     'lga': 'Warri South',    'ward': 'Ward 3'},
    {'vrn': 'IMO40235678UV', 'nin': '40234567891', 'full_name': 'Ngozi Eze',           'dob': '1996-05-18', 'gender': 'F', 'state': 'Imo',       'lga': 'Owerri Municipal','ward': 'Ward 2'},
    {'vrn': 'ADA50235678WX', 'nin': '50234567891', 'full_name': 'Yusuf Garba',         'dob': '1987-10-07', 'gender': 'M', 'state': 'Adamawa',   'lga': 'Yola North',     'ward': 'Ward 8'},
    {'vrn': 'BOR60235678YZ', 'nin': '60234567891', 'full_name': 'Halima Bukar',        'dob': '1998-04-22', 'gender': 'F', 'state': 'Borno',     'lga': 'Maiduguri',      'ward': 'Ward 5'},
    {'vrn': 'SOK70235678AA', 'nin': '70234567891', 'full_name': 'Suleiman Tanko',      'dob': '1990-07-11', 'gender': 'M', 'state': 'Sokoto',    'lga': 'Sokoto North',   'ward': 'Ward 1'},
    {'vrn': 'RIV80235678BB', 'nin': '80234567891', 'full_name': 'Ebele Amadi',         'dob': '1993-02-04', 'gender': 'F', 'state': 'Rivers',    'lga': 'Obio-Akpor',     'ward': 'Ward 10'},
    {'vrn': 'LAG90235678CC', 'nin': '90234567891', 'full_name': 'Tunde Ogundele',      'dob': '1986-11-29', 'gender': 'M', 'state': 'Lagos',     'lga': 'Alimosho',       'ward': 'Ward 4'},
    {'vrn': 'ENU11235678DD', 'nin': '11234567891', 'full_name': 'Chidinma Obiora',     'dob': '1995-06-16', 'gender': 'F', 'state': 'Enugu',     'lga': 'Enugu South',    'ward': 'Ward 2'},
    {'vrn': 'KAN21235678EE', 'nin': '21234567891', 'full_name': 'Aliyu Shehu',         'dob': '1992-09-09', 'gender': 'M', 'state': 'Kano',      'lga': 'Dala',           'ward': 'Ward 6'},
    {'vrn': 'OGU31235678FF', 'nin': '31234567891', 'full_name': 'Blessing Adeleke',    'dob': '1997-03-20', 'gender': 'F', 'state': 'Ogun',      'lga': 'Abeokuta South', 'ward': 'Ward 3'},
    {'vrn': 'PLA41235678GG', 'nin': '41234567891', 'full_name': 'Dauda Makarfi',       'dob': '1988-12-05', 'gender': 'M', 'state': 'Plateau',   'lga': 'Jos North',      'ward': 'Ward 7'},
    {'vrn': 'KWA51235678HH', 'nin': '51234567891', 'full_name': 'Rabi Usman',          'dob': '1994-07-27', 'gender': 'F', 'state': 'Kwara',     'lga': 'Ilorin West',    'ward': 'Ward 1'},
    {'vrn': 'EDO61235678II', 'nin': '61234567891', 'full_name': 'Obinna Agu',          'dob': '1991-10-13', 'gender': 'M', 'state': 'Edo',       'lga': 'Oredo',          'ward': 'Ward 5'},
    {'vrn': 'TAR71235678JJ', 'nin': '71234567891', 'full_name': 'Salamatu Haruna',     'dob': '1989-04-02', 'gender': 'F', 'state': 'Taraba',    'lga': 'Jalingo',        'ward': 'Ward 2'},
    {'vrn': 'NIG81235678KK', 'nin': '81234567891', 'full_name': 'Garba Lawan',         'dob': '1996-08-21', 'gender': 'M', 'state': 'Niger',     'lga': 'Minna',          'ward': 'Ward 4'},
    {'vrn': 'ABI91235678LL', 'nin': '91234567891', 'full_name': 'Ifeoma Onuoha',       'dob': '1993-01-08', 'gender': 'F', 'state': 'Abia',      'lga': 'Aba North',      'ward': 'Ward 6'},
]


def rand_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def rand_nin(used_nins: set) -> str:
    while True:
        nin = ''.join([str(random.randint(0, 9)) for _ in range(11)])
        if nin not in used_nins and not NIMCRecord.objects.filter(nin=nin).exists():
            used_nins.add(nin)
            return nin


def rand_email(name: str, used_emails: set) -> str:
    slug = name.lower().replace(' ', '.') + str(random.randint(10, 9999))
    domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'inecng.gov.ng']
    email = f"{slug}@{random.choice(domains)}"
    while email in used_emails or ElectoralUser.objects.filter(email=email).exists():
        email = f"{slug}{random.randint(1, 999)}@{random.choice(domains)}"
    used_emails.add(email)
    return email


def get_lga(state: str) -> str:
    return random.choice(STATE_LGAS.get(state, DEFAULT_LGA))


class Command(BaseCommand):
    help = 'Seeds the database with comprehensive mock data including VRN records.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing seeded data before seeding')

    def handle(self, *args, **options):
        if options.get('clear'):
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            AccreditationApplication.objects.all().delete()
            StaffInvitation.objects.all().delete()
            DisputeLog.objects.all().delete()
            ResultSheet.objects.all().delete()
            ElectionParticipation.objects.all().delete()
            Candidate.objects.all().delete()
            Election.objects.all().delete()
            ElectoralUser.objects.filter(is_superuser=False).exclude(username='99999999999').delete()
            PollingUnit.objects.all().delete()
            NIMCRecord.objects.exclude(nin='99999999999').delete()
            VoterRegistrationRecord.objects.all().delete()
            self.stdout.write('Cleared.')

        used_nins: set = set(NIMCRecord.objects.values_list('nin', flat=True))
        used_emails: set = set(ElectoralUser.objects.values_list('email', flat=True))

        # ── 1. NIMC RECORDS ──────────────────────────────────────────────────
        self.stdout.write('Seeding NIMCRecords...')
        nimc_bulk = []
        # First ensure all fixed VRN NIMs exist in NIMC
        fixed_nins = {r['nin'] for r in FIXED_VRN_RECORDS}
        for r in FIXED_VRN_RECORDS:
            if not NIMCRecord.objects.filter(nin=r['nin']).exists():
                nimc_bulk.append(NIMCRecord(
                    nin=r['nin'],
                    full_name=r['full_name'],
                    state=r['state'],
                    lga=r['lga'],
                    biometric_hash=f"bvn_biometric_{uuid.uuid4().hex}"
                ))
            used_nins.add(r['nin'])
        # Extra random NIMC records
        for _ in range(50):
            state = random.choice(NIGERIAN_STATES)
            nin = rand_nin(used_nins)
            nimc_bulk.append(NIMCRecord(
                nin=nin,
                full_name=rand_name(),
                state=state,
                lga=get_lga(state),
                biometric_hash=f"bvn_biometric_{uuid.uuid4().hex}"
            ))
        NIMCRecord.objects.bulk_create(nimc_bulk, ignore_conflicts=True)
        all_nimc = list(NIMCRecord.objects.all())
        self.stdout.write(self.style.SUCCESS(f'  NIMCRecords: {NIMCRecord.objects.count()} total'))

        # ── 2. VOTER REGISTRATION RECORDS (VRN) ───────────────────────────────
        self.stdout.write('Seeding VoterRegistrationRecords (25 fixed)...')
        for r in FIXED_VRN_RECORDS:
            VoterRegistrationRecord.objects.get_or_create(
                vrn=r['vrn'],
                defaults={
                    'nin': r['nin'],
                    'full_name': r['full_name'],
                    'date_of_birth': r['dob'],
                    'gender': r['gender'],
                    'state': r['state'],
                    'lga': r['lga'],
                    'ward': r.get('ward', ''),
                    'polling_unit_code': '',
                    'is_claimed': False,
                }
            )
        self.stdout.write(self.style.SUCCESS(f'  VoterRegistrationRecords: {VoterRegistrationRecord.objects.count()} total'))

        # ── 3. POLLING UNITS ──────────────────────────────────────────────────
        self.stdout.write('Seeding PollingUnits (30)...')
        pu_bulk = []
        existing_pu_ids = set(PollingUnit.objects.values_list('id', flat=True))
        for i in range(30):
            state = random.choice(NIGERIAN_STATES)
            lga = get_lga(state)
            ward = f"Ward {random.randint(1, 20)}"
            facility = random.choice(FACILITY_TYPES)
            while True:
                pu_id = f"PU-{random.randint(100000, 999999)}"
                if pu_id not in existing_pu_ids:
                    existing_pu_ids.add(pu_id)
                    break
            pu_bulk.append(PollingUnit(
                id=pu_id,
                name=f"{lga} {facility} PU {i + 1}",
                ward=ward,
                lga=lga,
                state=state,
                registered_voters_count=random.randint(300, 2500)
            ))
        PollingUnit.objects.bulk_create(pu_bulk, ignore_conflicts=True)
        all_pus = list(PollingUnit.objects.all())
        self.stdout.write(self.style.SUCCESS(f'  PollingUnits: {PollingUnit.objects.count()} total'))

        # ── 4. ELECTIONS ──────────────────────────────────────────────────────
        self.stdout.write('Seeding Elections...')
        for cfg in ELECTION_CONFIGS:
            Election.objects.get_or_create(
                id=cfg['id'],
                defaults={
                    'title': cfg['title'],
                    'election_type': cfg['type'],
                    'status': cfg['status'],
                    'date': cfg['date'],
                    'eligible_states': cfg['eligible_states'],
                    'description': f"Official INEC {cfg['title']} as scheduled.",
                }
            )
        all_elections = list(Election.objects.all())
        self.stdout.write(self.style.SUCCESS(f'  Elections: {Election.objects.count()} total'))

        # ── 5. CANDIDATES ──────────────────────────────────────────────────────
        self.stdout.write('Seeding Candidates...')
        cand_bulk = []
        existing_cand_ids = set(Candidate.objects.values_list('id', flat=True))
        for election in all_elections:
            n_candidates = random.randint(4, len(PARTIES))
            selected_parties = random.sample(PARTIES, n_candidates)
            for party_name, abbr, color in selected_parties:
                cand_id = f"{election.id}-{abbr.lower()}"
                if cand_id in existing_cand_ids:
                    continue
                existing_cand_ids.add(cand_id)
                cand_bulk.append(Candidate(
                    id=cand_id,
                    election=election,
                    name=rand_name(),
                    party=party_name,
                    party_abbr=abbr,
                    color=color,
                    manifesto=f"Our vision: quality education, security, and transparent governance under the {party_name}.",
                    running_mate=rand_name() if election.election_type in ['presidential', 'gubernatorial'] else None,
                    votes_count=random.randint(0, 50000) if election.status in ['active', 'collation', 'closed'] else 0
                ))
        Candidate.objects.bulk_create(cand_bulk, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'  Candidates: {Candidate.objects.count()} total'))

        # ── 6. ELECTORAL STAFF ────────────────────────────────────────────────
        self.stdout.write('Seeding ElectoralUser staff (30)...')
        ROLE_DISTRIBUTION = [
            ('commissioner', 'Lagos', 3),
            ('commissioner', 'Kano', 2),
            ('po', None, 8),
            ('apo', None, 5),
            ('spo', None, 3),
            ('co', None, 5),
            ('ro', None, 3),
            ('auditor', None, 1),
        ]
        created_staff = []
        for role, fixed_state, count in ROLE_DISTRIBUTION:
            for _ in range(count):
                nimc = random.choice(all_nimc)
                if ElectoralUser.objects.filter(username=nimc.nin).exists():
                    continue
                state = fixed_state or nimc.state
                email = rand_email(nimc.full_name, used_emails)
                try:
                    user = ElectoralUser(
                        username=nimc.nin,
                        email=email,
                        full_name=nimc.full_name,
                        state=state,
                        lga=nimc.lga,
                        role=role,
                        is_verified=True,
                        is_staff=True,
                        is_active=True,
                    )
                    user.password = make_password('Password2026!')
                    user.save()
                    created_staff.append(user)
                except Exception:
                    continue

        self.stdout.write(self.style.SUCCESS(f'  ElectoralUsers: {ElectoralUser.objects.count()} total'))

        # ── 7. ASSIGN POs AND COs TO POLLING UNITS ───────────────────────────
        po_list = list(ElectoralUser.objects.filter(role='po'))
        co_list = list(ElectoralUser.objects.filter(role='co'))
        if po_list and co_list:
            pus_to_update = []
            for i, pu in enumerate(all_pus):
                pu.presiding_officer = po_list[i % len(po_list)]
                pu.collation_officer = co_list[i % len(co_list)]
                pus_to_update.append(pu)
            PollingUnit.objects.bulk_update(pus_to_update, ['presiding_officer', 'collation_officer'])

        # ── 8. RESULT SHEETS ──────────────────────────────────────────────────
        self.stdout.write('Seeding ResultSheets (20)...')
        active_elections = [e for e in all_elections if e.status in ['active', 'collation', 'closed']]
        po_users = list(ElectoralUser.objects.filter(role='po'))
        rs_bulk = []
        if active_elections and po_users:
            for _ in range(20):
                election = random.choice(active_elections)
                pu = random.choice(all_pus)
                po = random.choice(po_users)
                accredited = random.randint(200, 1500)
                cast = random.randint(100, accredited)
                rs_bulk.append(ResultSheet(
                    id=uuid.uuid4(),
                    election=election,
                    polling_unit=pu,
                    presiding_officer=po,
                    scanned_form_url=f"https://irev.inec.gov.ng/forms/{uuid.uuid4().hex}.pdf",
                    accredited_voters=accredited,
                    total_votes_cast=cast,
                    po_digital_signature=f"SIG-{po.staff_number}-{uuid.uuid4().hex[:8].upper()}",
                    is_countersigned_by_agents=random.choice([True, False]),
                ))
            ResultSheet.objects.bulk_create(rs_bulk, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'  ResultSheets: {ResultSheet.objects.count()} total'))

        # ── 9. DISPUTE LOGS ───────────────────────────────────────────────────
        self.stdout.write('Seeding DisputeLogs (20)...')
        agents = list(ElectoralUser.objects.filter(role__in=['agent', 'observer', 'po']))
        DISPUTE_DESCRIPTIONS = [
            'Reported overvoting suspected at this polling unit.',
            'Technical fault with the BVAS device caused delays.',
            'Agent was unlawfully excluded from the polling booth.',
            'Voters were seen being coerced outside the facility.',
            'Ballot papers were not sufficient for all registered voters.',
            'Collation officer arrived over 2 hours late.',
        ]
        if agents and all_pus:
            dispute_bulk = [
                DisputeLog(
                    polling_unit=random.choice(all_pus),
                    raised_by=random.choice(agents),
                    description=random.choice(DISPUTE_DESCRIPTIONS),
                    is_resolved=random.choice([True, False]),
                ) for _ in range(20)
            ]
            DisputeLog.objects.bulk_create(dispute_bulk)
        self.stdout.write(self.style.SUCCESS(f'  DisputeLogs: {DisputeLog.objects.count()} total'))

        # ── 10. STAFF INVITATIONS ─────────────────────────────────────────────
        self.stdout.write('Seeding StaffInvitations (20)...')
        invite_senders = list(ElectoralUser.objects.filter(role__in=['secretary', 'commissioner']))
        if invite_senders:
            inv_bulk = []
            from api.utils import generate_staff_id
            for i in range(20):
                role = random.choice(['po', 'apo', 'spo', 'co', 'ro', 'auditor'])
                assigned_pu = random.choice(all_pus) if role in ['po', 'apo', 'spo'] else None
                state_for_id = assigned_pu.state if assigned_pu else 'Federal'
                
                inv_bulk.append(StaffInvitation(
                    token=secrets.token_urlsafe(32),
                    invited_email=f"staff.invite{i}.{random.randint(100,999)}@inec-candidate.gov.ng",
                    staff_number=generate_staff_id(role, state_for_id),
                    role=role,
                    assigned_polling_unit=assigned_pu,
                    invited_by=random.choice(invite_senders),
                    is_used=random.choice([True, False]),
                    expires_at=timezone.now() + timedelta(days=random.randint(-5, 30))
                ))
            StaffInvitation.objects.bulk_create(inv_bulk, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'  StaffInvitations: {StaffInvitation.objects.count()} total'))

        # ── 11. ACCREDITATION APPLICATIONS ───────────────────────────────────
        self.stdout.write('Seeding AccreditationApplications (20)...')
        used_acc_emails: set = set(AccreditationApplication.objects.values_list('contact_email', flat=True))
        acc_bulk = []
        for i in range(20):
            a_type = random.choice(['media', 'observer', 'intl_observer'])
            org_pool = MEDIA_ORGS if a_type == 'media' else OBSERVER_ORGS
            org_name = random.choice(org_pool) + f" — Unit {i + 1}"
            email = f"accred{i}.{random.randint(100,9999)}@org{i}.ng"
            while email in used_acc_emails:
                email = f"accred{i}.{random.randint(10000,99999)}@org{i}.ng"
            used_acc_emails.add(email)
            acc_bulk.append(AccreditationApplication(
                organization_name=org_name,
                applicant_type=a_type,
                contact_name=rand_name(),
                contact_email=email,
                contact_phone=f"0{random.randint(700,909)}{random.randint(1000000,9999999)}",
                organization_id=f"CAC-{random.randint(100000,999999)}",
                mandate_description=f"Independent coverage/oversight for the 2027 elections on behalf of {org_name}.",
                status=random.choice(['pending', 'pending', 'approved', 'rejected']),
            ))
        AccreditationApplication.objects.bulk_create(acc_bulk, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f'  AccreditationApplications: {AccreditationApplication.objects.count()} total'))

        # ── SUMMARY ───────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('═══════════════════════════════════════════════════'))
        self.stdout.write(self.style.SUCCESS(' ✅  Database seeding complete!'))
        self.stdout.write(self.style.SUCCESS('═══════════════════════════════════════════════════'))
        self.stdout.write(f'  NIMCRecord                 : {NIMCRecord.objects.count()}')
        self.stdout.write(f'  VoterRegistrationRecord    : {VoterRegistrationRecord.objects.count()}')
        self.stdout.write(f'  PollingUnit                : {PollingUnit.objects.count()}')
        self.stdout.write(f'  ElectoralUser (total)      : {ElectoralUser.objects.count()}')
        self.stdout.write(f'    → Staff (all roles)      : {ElectoralUser.objects.filter(is_staff=True).count()}')
        self.stdout.write(f'  Election                   : {Election.objects.count()}')
        self.stdout.write(f'  Candidate                  : {Candidate.objects.count()}')
        self.stdout.write(f'  ResultSheet                : {ResultSheet.objects.count()}')
        self.stdout.write(f'  DisputeLog                 : {DisputeLog.objects.count()}')
        self.stdout.write(f'  StaffInvitation            : {StaffInvitation.objects.count()}')
        self.stdout.write(f'  AccreditationApplication   : {AccreditationApplication.objects.count()}')
        self.stdout.write('')
        self.stdout.write('  Staff password             : Password2026!')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('  VRN Test Credentials (use these on the signup page):'))
        self.stdout.write('  ┌──────────────────────┬─────────────────┬──────────────────────┐')
        self.stdout.write('  │ VRN                  │ NIN             │ Full Name            │')
        self.stdout.write('  ├──────────────────────┼─────────────────┼──────────────────────┤')
        for r in FIXED_VRN_RECORDS[:8]:
            self.stdout.write(f"  │ {r['vrn']:<20} │ {r['nin']:<15} │ {r['full_name']:<20} │")
        self.stdout.write('  └──────────────────────┴─────────────────┴──────────────────────┘')
        self.stdout.write('  (25 VRN records total — see FIXED_VRN_RECORDS in seed_data.py for full list)')
