import random
import string
from datetime import datetime

STATE_CODES = {
    'Abia': 'ABI',
    'Adamawa': 'ADA',
    'Akwa Ibom': 'AKW',
    'Anambra': 'ANA',
    'Bauchi': 'BAU',
    'Bayelsa': 'BAY',
    'Benue': 'BEN',
    'Borno': 'BOR',
    'Cross River': 'CRO',
    'Delta': 'DEL',
    'Ebonyi': 'EBO',
    'Edo': 'EDO',
    'Ekiti': 'EKI',
    'Enugu': 'ENU',
    'FCT': 'FCT',
    'Gombe': 'GOM',
    'Imo': 'IMO',
    'Jigawa': 'JIG',
    'Kaduna': 'KAD',
    'Kano': 'KAN',
    'Katsina': 'KAT',
    'Kebbi': 'KEB',
    'Kogi': 'KOG',
    'Kwara': 'KWA',
    'Lagos': 'LAG',
    'Nasarawa': 'NAS',
    'Niger': 'NIG',
    'Ogun': 'OGU',
    'Ondo': 'OND',
    'Osun': 'OSU',
    'Oyo': 'OYO',
    'Plateau': 'PLA',
    'Rivers': 'RIV',
    'Sokoto': 'SOK',
    'Taraba': 'TAR',
    'Yobe': 'YOB',
    'Zamfara': 'ZAM',
}

ROLE_CODES = {
    'commissioner': 'COM',
    'secretary': 'SEC',
    'po': 'PO',
    'apo': 'APO',
    'spo': 'SPO',
    'co': 'CO',
    'ro': 'RO',
    'auditor': 'AUD',
    'observer': 'OBS',
    'media': 'MED',
    'agent': 'AGT',
}


def generate_voter_id(state):
    """
    Generates a 19-character VIN matching real INEC format.
    Format: [3-letter state code][13 digits][2 letters]
    Example: LAG1234567890123IK
    """
    from .models import ElectoralUser

    state_code = STATE_CODES.get(state, state[:3].upper())

    while True:
        numbers = ''.join(random.choices(string.digits, k=13))
        letters = ''.join(random.choices(string.ascii_uppercase, k=2))
        vin = f"{state_code}{numbers}{letters}"
        if not ElectoralUser.objects.filter(voter_id=vin).exists():
            return vin


def generate_staff_id(role, state):
    """
    Generates a realistic INEC staff ID.
    Format: INEC/[STATE]/[ROLE]/[YEAR]/[6-DIGIT]
    Example: INEC/LAG/COM/2026/483921
    """
    from .models import ElectoralUser

    role_code = ROLE_CODES.get(role, role[:3].upper())
    state_code = STATE_CODES.get(state, state[:3].upper())
    year = datetime.now().year

    while True:
        number = str(random.randint(100000, 999999))
        staff_id = f"INEC/{state_code}/{role_code}/{year}/{number}"
        if not ElectoralUser.objects.filter(staff_number=staff_id).exists():
            return staff_id