from apps.adminpage import models as adminpage_model
from apps.users.models import User


def check_field_action(action):
    return action in [adminpage_model.ACTION_ADD, adminpage_model.ACTION_DELETE, adminpage_model.ACTION_UPDATE]


def get_emails_from_user_ids(user_ids: list) -> list:
    emails = User.objects.filter(
        id__in=user_ids,
        email__isnull=False,
        email__iregex=r'[^\s]'
    ).values_list('email', flat=True)
    return list(emails)
