from __future__ import absolute_import, unicode_literals
from celery import shared_task

from django.utils import timezone
from datetime import timedelta

from django.template.loader import render_to_string
from django.conf import settings
from apps.users import models as user_models
from apps.adminpage import models as adminpage_models
from apps.adminpage import utils as adminpage_utils
from django.db.models import Sum

from apps.core.tasks import send_email, push_notification


def generate_confirm_link(email):
    user = user_models.User.objects.get(email=email)
    token = user_models.ConfirmEmailToken.objects.create(user=user)
    return '{host}/confirm/{token}/'.format(host=settings.SERVER_URL, token=token.token)


def generate_forgot_link(email):
    user = user_models.User.objects.get(email=email)
    reset_token = user_models.ResetToken.objects.create(user=user)
    return '{host}/forgot-link/{token}'.format(host=settings.SERVER_URL, token=reset_token.reset_token)


@shared_task
def send_register_confirm_email(to_email):
    confirm_link = generate_confirm_link(to_email)
    subject = '[Haui Chat App] Register Confirmation'
    context = {'confirm_link': confirm_link}
    body_html = render_to_string('emails/register_confirm.html', context)
    send_email.delay(
        subject=subject,
        body_html=body_html,
        from_email=settings.EMAIL_NO_REPLY,
        recipient_list=[to_email]
    )


@shared_task
def send_forgot_password_email(to_email):
    forgot_link = generate_forgot_link(to_email)
    subject = '[Sixcent English App] Forgot password'
    context = {'forgot_link': forgot_link}
    body_html = render_to_string('emails/forgot_password.html', context)
    send_email.delay(
        subject=subject,
        body_html=body_html,
        from_email=settings.EMAIL_NO_REPLY,
        recipient_list=[to_email]
    )


TITLE_LOGIN_REMINDER = 'time not login'
BODY_LOGIN_REMINDER = 'time not login'


@shared_task
def login_information_system():
    user_login_history = user_models.LoginHistory.objects.order_by('user_id', '-end_date').distinct('user_id')
    user_ids = user_login_history.filter(
        end_date__lte=timezone.now().date() - timedelta(days=settings.TIME_NOT_LOGIN)
    ).values_list('user_id', flat=True)

    list_email = adminpage_utils.get_emails_from_user_ids(user_ids)

    push_notification.delay(
        user_ids=list(user_ids),
        title=TITLE_LOGIN_REMINDER,
        body=BODY_LOGIN_REMINDER,
        notify_type=adminpage_models.NOTIFY_TYPE_LOGIN_REMINDER
    )
    send_email.delay(
        subject=TITLE_LOGIN_REMINDER,
        body_html=BODY_LOGIN_REMINDER,
        from_email=settings.EMAIL_NO_REPLY,
        recipient_list=list(list_email)
    )


TITLE_RATING_APP = 'rating app'
BODY_RATING_APP = 'rating app'


@shared_task
def rating_app_push_notify():
    user_ids_rating_app = user_models.Rating.objects.all().values_list('user_id', flat=True)
    user_ids = user_models.User.objects.exclude(id__in=user_ids_rating_app).values_list('id', flat=True)
    user_ids = user_models.LoginHistory.objects.filter(
        user_id__in=user_ids
    ).values('user_id').annotate(
        num_login=Sum('num_date')
    ).filter(num_login__gt=settings.RATING_TIME_LOGIN).values_list('user_id', flat=True)

    push_notification.delay(
        user_ids=list(user_ids),
        title=TITLE_RATING_APP,
        body=BODY_RATING_APP,
        notify_type=adminpage_models.NOTIFY_TYPE_RATING_APP
    )
