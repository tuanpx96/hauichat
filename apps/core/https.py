from django.http import HttpResponseRedirect

SIXCENTS_PROTOCOL = 'hauichat'


class HttpHauichatResponseRedirect(HttpResponseRedirect):
    allowed_schemes = [SIXCENTS_PROTOCOL]
