import boto3
from botocore.exceptions import ClientError
from celery import Task, shared_task
from celery.utils.log import get_task_logger

from fcm_django.models import FCMDevice

from django.conf import settings
from django.utils import timezone

_logger = get_task_logger(__name__)


class GGCLOUDSESTask(Task):
    """GGCLOUD Simple Email Service Task"""
    _client = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                'ses',
                ggcloud_access_key_id=settings.GGCLOUD_ACCESS_KEY_ID,
                ggcloud_secret_access_key=settings.GGCLOUD_SECRET_ACCESS_KEY,
                region_name=settings.GGCLOUD_REGION)
        return self._client


@shared_task(base=GGCLOUDSESTask, bind=True)
def send_email(self, subject, body_html, from_email, recipient_list, body_text=None):
    CHARSET = 'UTF-8'
    message = {
        'Body': {
            'Html': {
                'Charset': CHARSET,
                'Data': body_html,
            },
        },
        'Subject': {
            'Charset': CHARSET,
            'Data': subject,
        },
    }
    if body_text:
        message['Body']['Text'] = {
            'Charset': CHARSET,
            'Data': body_text,
        }

    try:
        self.client.send_email(
            Destination={'ToAddresses': recipient_list},
            Message=message,
            Source=from_email,
        )
    except ClientError as e:
        _logger.error(e.response['Error']['Message'])


@shared_task
def push_notification(user_ids: list = None, title: str = None, body: str = None, notify_type: str = None):
    """Push a notification to user devices, get from user_ids

    If user_ids is None, will send to all devices
    """
    devices = FCMDevice.objects.all()
    if user_ids:
        devices = devices.filter(user_id__in=user_ids)

    data = {
        'notify_type': notify_type,
    }
    devices.send_message(title=title, body=body, data=data)


@shared_task(ignore_result=True)
def debug_task():
    # Only for debug
    _logger.info('Excecute Debug Task at {}'.format(timezone.now()))
