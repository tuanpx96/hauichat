import logging

from django.contrib.auth import authenticate
from django.shortcuts import render
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from apps.core.https import HttpHauichatResponseRedirect, SIXCENTS_PROTOCOL
from apps.users import models as user_models
from apps.users import serializers as user_sers
from apps.users import utils as user_utils
from apps.users.tasks import (
    send_forgot_password_email, send_register_confirm_email,
)

_logger = logging.getLogger(__name__)


class LoginEmailAPI(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        validator = user_sers.LoginEmailValidator(data=request.data)
        if not validator.is_valid():
            _logger.error(validator.errors)
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        email = validator.validated_data['email']
        password = validator.validated_data['password']
        user = authenticate(email=email, password=password)
        if not user:
            _logger.error('Incorrect email: {} or password: ******'.format(email))
            return Response('Incorrect email or password', status=status.HTTP_401_UNAUTHORIZED)

        token = user_models.Token.objects.create(user=user)
        user.user_type = user_utils.get_user_type(user.id)
        data = {
            'access_token': token.key,
            'expired_time': user_utils.get_expired_time(token),
            'user': user
        }

        user_utils.create_or_update_login_history(user.id)
        serializer = user_sers.TokenSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResetPassword(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        validator = user_sers.ResetPasswordValidator(data=request.data)
        if not validator.is_valid():
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)
        reset_token = validator.validated_data['reset_token']
        password = validator.validated_data['password']
        try:
            reset_token = user_models.ResetToken.objects.get(reset_token=reset_token)
        except Exception:
            return Response('Not found reset token', status=status.HTTP_404_NOT_FOUND)

        user = reset_token.user
        if not user_utils.check_expired_time_reset_token(reset_token):
            reset_token.delete()
            return Response('Token has expired', status=status.HTTP_404_NOT_FOUND)

        user.set_password(password)
        user.save()

        reset_token.delete()
        user.user_type = user_utils.get_user_type(user.id)
        serializer = user_sers.UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LoginFacebookAPI(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        validator = user_sers.LoginFacebookValidator(data=request.data)
        if not validator.is_valid():
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        fb_access_token = validator.validated_data['fb_access_token']
        try:
            profiles = user_utils.get_facebook_profile(fb_access_token)
            fb_id = profiles['id']
            user_name = profiles['name']
        except Exception:
            return Response('Incorrect facebook id', status=status.HTTP_401_UNAUTHORIZED)

        user, created = user_models.User.objects.get_or_create(
            facebook_id=fb_id,
            defaults={'username': user_name}
        )

        token = user_models.Token.objects.create(user=user)
        user.user_type = user_utils.get_user_type(user.id)

        data = {
            'access_token': token.key,
            'expired_time': user_utils.get_expired_time(token),
            'user': user
        }

        user_utils.create_or_update_login_history(user.id)
        serializer = user_sers.TokenSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LoginLineAPI(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        validator = user_sers.LoginLineValidator(data=request.data)
        if not validator.is_valid():
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        line_access_token = validator.validated_data['line_access_token']
        try:
            profiles = user_utils.get_line_profile(line_access_token)
            line_id = profiles['userId']
            user_name = profiles['displayName']
        except Exception:
            return Response('Incorrect Line Id', status=status.HTTP_401_UNAUTHORIZED)

        user, created = user_models.User.objects.get_or_create(
            line_id=line_id,
            defaults={'username': user_name}
        )

        token = user_models.Token.objects.create(user=user)
        user.user_type = user_utils.get_user_type(user.id)
        data = {
            'access_token': token.key,
            'expired_time': user_utils.get_expired_time(token),
            'user': user
        }

        user_utils.create_or_update_login_history(user.id)
        serializer = user_sers.TokenSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RegisterEmailAPI(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        validator = user_sers.RegisterEmailValidator(data=request.data)
        if not validator.is_valid():
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        email = validator.validated_data['email']
        password = validator.validated_data['password']
        if user_models.User.objects.filter(email=email).exists():
            return Response('Email already exists', status=status.HTTP_409_CONFLICT)
        else:
            user = user_models.User(email=email, is_active=False)
            user.set_password(password)
            user.save()

        send_register_confirm_email.delay(email)

        serializer = user_sers.UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LogoutAPI(APIView):

    def post(self, request, format=None):
        user_models.Token.objects.filter(key=request.auth.key).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GetInfoUserAPI(APIView):

    def get(self, request, format=None):
        user_utils.create_or_update_login_history(request.user.id)
        user = request.user
        user.user_type = user_utils.get_user_type(user.id)
        serializer = user_sers.UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, format=None):
        validator = user_sers.UserUpdateValidator(data=request.data)
        if not validator.is_valid():
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        username = validator.validated_data.get('username')
        data = {'username': username}
        upd_fields = {k: v for k, v in data.items() if v is not None}

        if upd_fields:
            user_models.User.objects.filter(id=user.id).update(**upd_fields)
            user = user_models.User.objects.filter(id=user.id).first()

        serializer = user_sers.UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateFacbookIdAPI(APIView):

    def put(self, request, format=None):
        validator = user_sers.LoginFacebookValidator(data=request.data)
        if not validator.is_valid():
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        fb_access_token = validator.validated_data['fb_access_token']
        try:
            profiles = user_utils.get_facebook_profile(fb_access_token)
            fb_id = profiles['id']
        except Exception:
            return Response('Incorrect facebook id', status=status.HTTP_401_UNAUTHORIZED)

        user = request.user
        user_models.User.objects.filter(id=user.id).update(facebook_id=fb_id)
        user = user_models.User.objects.filter(id=user.id).first()
        serializer = user_sers.UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateUserPasswordAPI(APIView):

    def put(self, request, format=None):
        validator = user_sers.UserUpdatePasswordValidator(data=request.data)
        if not validator.is_valid():
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        old_password = validator.validated_data['old_password']
        new_password = validator.validated_data['new_password']
        user = request.user

        if not user.check_password(old_password):
            return Response('Password and old password dissimilar', status=status.HTTP_401_UNAUTHORIZED)

        user.set_password(new_password)
        user.save()
        serializer = user_sers.UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateLineIdAPI(APIView):

    def put(self, request, format=None):
        validator = user_sers.LoginLineValidator(data=request.data)
        if not validator.is_valid():
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        line_access_token = validator.validated_data['line_access_token']
        try:
            profiles = user_utils.get_line_profile(line_access_token)
            line_id = profiles['userId']
        except Exception:
            return Response('Incorrect Line Id', status=status.HTTP_401_UNAUTHORIZED)
        user = request.user

        user_models.User.objects.filter(id=user.id).update(line_id=line_id)
        user = user_models.User.objects.filter(id=user.id).first()
        serializer = user_sers.UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RatingAppServiceAPI(APIView):

    def put(self, request, format=None):
        validator = user_sers.RatingValidator(data=request.data)
        if not validator.is_valid():
            _logger.error(validator.errors)
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        num_stars = validator.validated_data['num_stars']
        comment = validator.validated_data['comment']

        rating, created = user_models.Rating.objects.update_or_create(
            user_id=request.user.id,
            defaults={
                'num_stars': num_stars,
                'comment': comment
            }
        )
        serializer = user_sers.RetingSerializer(rating)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ForgotPasswordAPI(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        validator = user_sers.ForgotPasswordValidator(data=request.data)
        if not validator.is_valid():
            _logger.error(validator.errors)
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)

        email = validator.validated_data['email']
        if not user_models.User.objects.filter(email=email).exists():
            _logger.error('Email already not exists')
            return Response('Email already not exists', status=status.HTTP_400_BAD_REQUEST)

        send_forgot_password_email.delay(email)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ConfirmEmailAPI(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, token):
        try:
            token = user_models.ConfirmEmailToken.objects.get(token=token)
        except ObjectDoesNotExist:
            err_msg = 'Confirm token not found {}'.format(token)
            _logger.error(err_msg)
            return render(request, 'users/confirm_email_failed.html')

        if not user_utils.check_expired_time_confirm_email_token(token):
            err_msg = 'Confirm token expired: {}'.format(token)
            _logger.error(err_msg)
            token.delete()
            return render(request, 'users/confirm_email_failed.html')

        user = token.user
        user.is_active = True
        user.save()
        token.delete()

        langoo_link = '{protocol}://sixcentsapp/confirm/{token}'.format(
            protocol=SIXCENTS_PROTOCOL, token=token.token)
        context = {'email': user.email, 'langoo_link': langoo_link}
        return render(request, 'users/confirm_email_success.html', context)


class ForgotLinkAPI(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(relf, request, token):
        forgot_link = '{protocol}://sixcentsapp/reset/{token}'.format(
            protocol=SIXCENTS_PROTOCOL, token=token)
        return HttpHauichatResponseRedirect(forgot_link)


class GetDetailNotifyAPI(APIView):

    def get(self, request, notify_id):
        try:
            notify = user_models.Notification.objects.get(id=notify_id)
        except ObjectDoesNotExist:
            err_msg = 'notify not Found: {}'.format(notify_id)
            _logger.error(err_msg)
            return Response(err_msg, status=status.HTTP_404_NOT_FOUND)

        user_notify = user_models.UserNotification.objects.get(
            user_id=request.user.id,
            notification_id=notify_id
        )
        user_notify.is_read = True
        user_notify.save()

        serializer = user_sers.DetailNotifySerializer(notify)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetListNotificationAPI(APIView):

    def get(self, request, format=None):
        validator = user_sers.NotifyValidator(data=request.GET)
        if not validator.is_valid():
            _logger.error(validator.errors)
            return Response(validator.errors, status=status.HTTP_400_BAD_REQUEST)
        user_notifications = user_models.UserNotification.objects.filter(user_id=request.user)
        notify_ids = user_notifications.values_list('notification_id', flat=True)
        notifications = user_models.Notification.objects.filter(id__in=notify_ids)
        page_size = validator.validated_data['page_size']
        paginator = PageNumberPagination()
        paginator.page_size = page_size
        paged_notifications = paginator.paginate_queryset(notifications, request)
        for notify in paged_notifications:
            notify.is_read = notify.user_notifications.get().is_read
        serializer = user_sers.ListNotifySerializer(paged_notifications, many=True)
        return paginator.get_paginated_response(serializer.data)
