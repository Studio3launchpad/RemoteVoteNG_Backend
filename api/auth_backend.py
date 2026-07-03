from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import ElectoralUser


class EVotingAuthBackend(ModelBackend):
    """
    Custom authentication backend that permits users to authenticate using
    either their NIN (stored in the username field) or their Staff Number.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username:
            return None
        
        try:
            # Query by username (NIN) OR staff_number
            user = ElectoralUser.objects.get(Q(username=username) | Q(staff_number=username))
            if user.check_password(password):
                return user
        except ElectoralUser.DoesNotExist:
            return None
        except Exception:
            return None
            
        return None
