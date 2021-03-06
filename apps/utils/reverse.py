from django.urls import reverse as djreverse
from django.conf import settings
from django.utils.http import urlencode

def reverse(name, kwargs={}):

    baseurl = ''
    if 'country_code' in kwargs and 'ar' == kwargs['country_code']:
        baseurl = 'https://cualbondi.com.ar'
        kwargs.pop('country_code')
    else:
        baseurl = 'https://cualbondi.org'

    get = kwargs.pop('get', {})
    r = djreverse(name, kwargs=kwargs)
    if get:
        r += '?' + urlencode(get)

    # baseurl = ''
    # if argentina == True:
    #     baseurl = 'https://cualbondi.com.ar'
    # elif argentina == False:
    #     baseurl = 'https://cualbondi.org'
    # else:
    #     baseurl = ''

    if settings.ENVIRONMENT != 'production':
        print(f'Reverse baseurl redirect ignored in dev mode: [{baseurl}] {r}')
        return 'https://localhost:8080' + r

    return baseurl + r
