from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Token, Rating, LoginHistory, Notification, UserNotification


class SixcentUserAdmin(UserAdmin):
    list_display = (
        'id', 'username', 'email', 'facebook_id', 'line_id',
        'is_active', 'is_staff', 'date_joined', 'last_login',
    )


class TokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'user', 'created')


class RatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'num_stars', 'comment', 'created_at')


class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'start_date', 'end_date', 'num_date')


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'body', 'notify_type', 'created_at')


class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'notification', 'is_read', 'created_at')


admin.site.register(User, SixcentUserAdmin)
admin.site.register(Token, TokenAdmin)
admin.site.register(Rating, RatingAdmin)
admin.site.register(LoginHistory, LoginHistoryAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(UserNotification, UserNotificationAdmin)
