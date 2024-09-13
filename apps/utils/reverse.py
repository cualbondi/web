from django.urls import reverse as djreverse
from django.conf import settings
from django.utils.http import urlencode

def reverse(name, kwargs={}):

    baseurl = ''

    if settings.ENVIRONMENT == 'production':
        if 'country_code' in kwargs and 'ar' == kwargs['country_code']:
            baseurl = 'https://cualbondi.com.ar'
            kwargs.pop('country_code')
        else:
            baseurl = 'https://cualbondi.com'
    else:
        # print(f'Reverse baseurl redirect ignored in dev mode: [{baseurl}] {r}')
        baseurl = 'http://localhost:8000'

    get = kwargs.pop('get', {})
    r = djreverse(name, kwargs=kwargs)
    if get:
        r += '?' + urlencode(get)

    return baseurl + r
