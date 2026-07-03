from django.db import migrations
from django.conf import settings

def provision_secretary(apps, schema_editor):
    ElectoralUser = apps.get_model('api', 'ElectoralUser')
    NIMCRecord = apps.get_model('api', 'NIMCRecord')
    
    # Retrieve configuration settings
    nin = getattr(settings, 'SECRETARY_NIN', '99999999999')
    staff_number = getattr(settings, 'SECRETARY_STAFF_NUMBER', 'STAFF-SECRETARY-2026')
    password = getattr(settings, 'SECRETARY_DEFAULT_PASSWORD', 'SecPass2026!')
    email = getattr(settings, 'SECRETARY_EMAIL', 'secretary@remotevoteng.org')
    full_name = getattr(settings, 'SECRETARY_NAME', 'INEC Secretary HQ')
    state = getattr(settings, 'SECRETARY_STATE', 'FCT')
    lga = getattr(settings, 'SECRETARY_LGA', 'Abuja Municipal')
    
    # 1. Create NIMC record if it doesn't exist
    NIMCRecord.objects.get_or_create(
        nin=nin,
        defaults={
            'full_name': full_name,
            'state': state,
            'lga': lga,
            'biometric_hash': 'mock_secretary_biometric_hash_2026'
        }
    )
    
    # 2. Create the Secretary user if it doesn't exist
    if not ElectoralUser.objects.filter(username=nin).exists():
        from django.contrib.auth.hashers import make_password
        
        ElectoralUser.objects.create(
            username=nin,
            email=email,
            password=make_password(password),
            full_name=full_name,
            state=state,
            lga=lga,
            role='secretary',
            staff_number=staff_number,
            is_verified=True,
            is_staff=True,
            is_active=True
        )

def remove_secretary(apps, schema_editor):
    ElectoralUser = apps.get_model('api', 'ElectoralUser')
    NIMCRecord = apps.get_model('api', 'NIMCRecord')
    nin = getattr(settings, 'SECRETARY_NIN', '99999999999')
    ElectoralUser.objects.filter(username=nin).delete()
    NIMCRecord.objects.filter(nin=nin).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_pollingunit_collation_officer_and_more'),
    ]

    operations = [
        migrations.RunPython(provision_secretary, reverse_code=remove_secretary),
    ]
