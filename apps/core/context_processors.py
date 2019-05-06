# -*- coding: UTF-8 -*-
from django.conf import settings


def home_url(request):
    return {'HOME_URL': settings.HOME_URL}


def facebook_app_id(request):
    return {'FACEBOOK_APP_ID': settings.FACEBOOK_APP_ID}
