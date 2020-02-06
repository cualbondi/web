from django.urls import reverse as djreverse
from django.conf import settings

def reverse(name, kwargs={}, argentina=None):
    r = djreverse(name, kwargs=kwargs)

    baseurl = ''
    if argentina == True:
        baseurl = 'https://cualbondi.com.ar'
    elif argentina == False:
        baseurl = 'https://cualbondi.org'
    else:
        baseurl = ''

    if settings.ENVIRONMENT == 'production':
        return baseurl + r
    else:
        print(f'Reverse baseurl redirect ignored in dev mode: [{baseurl}] {r}')
        return 'https://localhost:8080' + r
