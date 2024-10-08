"""
Base settings to build other settings files upon.
"""

import environ

def gettext_noop(s):
    return s

ROOT_DIR = environ.Path(__file__) - 3  # (web/config/settings/base.py - 3 = web/)
APPS_DIR = ROOT_DIR.path('apps')

env = environ.Env()

READ_DOT_ENV_FILE = env.bool('DJANGO_READ_DOT_ENV_FILE', default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(ROOT_DIR.path('.env')))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool('DJANGO_DEBUG', False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = 'UTC'
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
LOCALE_PATHS = [
    str(ROOT_DIR.path('locale')),
]
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = False
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env.get_value("POSTGRES_DB"),
        'USER': env.get_value("POSTGRES_USER"),
        'PASSWORD': env.get_value("POSTGRES_PASSWORD"),
        'HOST': env.get_value("DB_HOST"),
        'PORT': '5432',
        # 'OPTIONS': {
        #     'pool': {'min_size': 10, 'max_size': 100},
        # },
        'CONN_MAX_AGE': env.int('CONN_MAX_AGE', default=60),
        'ATOMIC_REQUESTS': True,
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = 'config.urls'
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = 'config.wsgi.application'

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'django.contrib.humanize', # Handy template tags
    'django.contrib.admin',
    'django.contrib.gis',
    'django.contrib.flatpages',
    'django.contrib.sitemaps',
    'django.contrib.postgres',
]
THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'imagekit',
    'django_extensions',

    # social auth
    'oauth2_provider',
    'social_django',
    'rest_framework_social_oauth2',
    'treebeard',
    'django_comments',
]
LOCAL_APPS = [
    'apps.usuarios.apps.UsuariosConfig',
    'apps.core.apps.CoreConfig',
    'apps.catastro.apps.CatastroConfig',
    'apps.editor.apps.EditorConfig',
    'apps.api3.apps.Api3Config',
    'apps.reviews.apps.ReviewsConfig',
]

# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
COMMENTS_APP = 'apps.reviews'

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {
}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
# AUTH_USER_MODEL = 'users.User'
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
# LOGIN_REDIRECT_URL = 'users:redirect'
LOGIN_REDIRECT_URL = '/'
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = 'account_login'

ABSOLUTE_URL_OVERRIDES = {
    'auth.user': lambda u: "/usuarios/%s/" % u.username,
}

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # 'apps.core.middlewares.auth.AuthenticationMiddleware',
    'apps.core.middlewares.log.LoggingMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.core.middlewares.locale.LocaleMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'apps.core.middleware.WhodidMiddleware',
    # 'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
]

IGNORE_AUTH_URL_PATTERNS = [
    '^/$',
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(ROOT_DIR('staticfiles'))
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [
    str(APPS_DIR.path('static')),
]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR('media'))
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = 'media/'

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'DIRS': [
            str(ROOT_DIR.path('templates_jinja2')),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'environment': 'config.settings.jinja2.environment',
        },
    },
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        'DIRS': [
            str(APPS_DIR.path('templates')),
            str(ROOT_DIR.path('templates')),
        ],
        'OPTIONS': {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
            'debug': DEBUG,
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                # 'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.contrib.messages.context_processors.messages',

                'apps.core.context_processors.home_url',
                'apps.core.context_processors.facebook_app_id',
                'apps.core.context_processors.ciudades',

                # TODO: revisar si necesitamos estos dos https://github.com/RealmTeam/django-rest-framework-social-oauth2
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (
    str(APPS_DIR.path('fixtures')),
)

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env('DJANGO_EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.
ADMIN_URL = r'^admin/'
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [
    ("""Julian Perelli, Federico Marcos""", 'marcosfede@gmail.com'),
]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS


# ARCGIS GEOCODER
# ------------------------------------------------------------------------------
ARCGIS_USER = env('ARCGIS_USER', default='')
ARCGIS_PASS = env('ARCGIS_PASS', default='')


# Your stuff...
# ------------------------------------------------------------------------------

GEOCODING_GOOGLE_KEY = env('GEOCODING_GOOGLE_KEY', default='')

# Variables personalizadas
RADIO_ORIGEN_DEFAULT = 200
RADIO_DESTINO_DEFAULT = 200
LONGITUD_PAGINA = 5

HOME_URL = env.get_value('HOME_URL', default='https://localhost:8080')
FACEBOOK_APP_ID = env.get_value('FACEBOOK_APP_ID', default='')
API_URL = env.get_value('API_URL', default='')

# SOCIAL AUTH
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
        'rest_framework_social_oauth2.authentication.SocialAuthentication',
    ],
    'EXCEPTION_HANDLER': 'apps.api3.exceptions.exception_handler',
}
DRFSO2_PROPRIETARY_BACKEND_NAME = 'Facebook'
AUTHENTICATION_BACKENDS = [
    # Facebook OAuth2
    'social_core.backends.facebook.FacebookAppOAuth2',
    'social_core.backends.facebook.FacebookOAuth2',
    # django-rest-framework-social-oauth2
    'rest_framework_social_oauth2.backends.DjangoOAuth2',
    # Django
    'django.contrib.auth.backends.ModelBackend',
]

SOCIAL_AUTH_PIPELINE = [
    # Get the information we can about the user and return it in a simple
    # format to create the user instance later. On some cases the details are
    # already part of the auth response from the provider, but sometimes this
    # could hit a provider API.
    'social_core.pipeline.social_auth.social_details',

    # Get the social uid from whichever service we're authing thru. The uid is
    # the unique identifier of the given user in the provider.
    'social_core.pipeline.social_auth.social_uid',

    # Verifies that the current auth process is valid within the current
    # project, this is where emails and domains whitelists are applied (if
    # defined).
    'social_core.pipeline.social_auth.auth_allowed',

    # Checks if the current social-account is already associated in the site.
    'social_core.pipeline.social_auth.social_user',

    # Make up a username for this person, appends a random string at the end if
    # there's any collision.
    'social_core.pipeline.user.get_username',

    # Send a validation email to the user to verify its email address.
    # Disabled by default.
    # 'social_core.pipeline.mail.mail_validation',

    # Associates the current social details with another user account with
    # a similar email address. Disabled by default.
    'social_core.pipeline.social_auth.associate_by_email',

    # Create a user account if we haven't found one yet.
    'social_core.pipeline.user.create_user',

    # Create the record that associates the social account with the user.
    'social_core.pipeline.social_auth.associate_user',

    # Populate the extra_data field in the social record with the values
    # specified by settings (and the default ones like access_token, etc).
    'social_core.pipeline.social_auth.load_extra_data',

    # Update the user record with any changed info from the auth service.
    'social_core.pipeline.user.user_details',
]

# Facebook configuration
SOCIAL_AUTH_FACEBOOK_KEY = '516530425068934'
SOCIAL_AUTH_FACEBOOK_SECRET = env.get_value("SOCIAL_AUTH_FACEBOOK_SECRET", default='add the secret please')
# Define SOCIAL_AUTH_FACEBOOK_SCOPE to get extra permissions from facebook. Email is not sent by default, to get it, you must request the email permission:
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']
SOCIAL_AUTH_FACEBOOK_PROFILE_EXTRA_PARAMS = {
    'fields': 'id, name, email'
}
DRFSO2_URL_NAMESPACE = 'drfsocial'
SOCIAL_AUTH_URL_NAMESPACE = 'drfsocial'

SHELL_PLUS_PRINT_SQL = True

LANGUAGES = [
    # ('af', gettext_noop('Afrikaans')),
    ('ar', 'العربية'),
    # ('ar-dz', gettext_noop('Algerian Arabic')),
    # ('ast', gettext_noop('Asturian')),
    # ('az', gettext_noop('Azerbaijani')),
    # ('bg', gettext_noop('Bulgarian')),
    # ('be', gettext_noop('Belarusian')),
    # ('bn', gettext_noop('Bengali')),
    # ('br', gettext_noop('Breton')),
    # ('bs', gettext_noop('Bosnian')),
    # ('ca', gettext_noop('Catalan')),
    # ('cs', gettext_noop('Czech')),
    # ('cy', gettext_noop('Welsh')),
    # ('da', gettext_noop('Danish')),
    ('de', 'Deutsch'),
    # ('dsb', gettext_noop('Lower Sorbian')),
    # ('el', gettext_noop('Greek')),
    ('en', 'English'),
    # ('en-au', gettext_noop('Australian English')),
    # ('en-gb', gettext_noop('British English')),
    # ('eo', gettext_noop('Esperanto')),
    ('es', 'Español'),
    # ('es-ar', gettext_noop('Argentinian Spanish')),
    # ('es-co', gettext_noop('Colombian Spanish')),
    # ('es-mx', gettext_noop('Mexican Spanish')),
    # ('es-ni', gettext_noop('Nicaraguan Spanish')),
    # ('es-ve', gettext_noop('Venezuelan Spanish')),
    # ('et', gettext_noop('Estonian')),
    # ('eu', gettext_noop('Basque')),
    ('fa', 'فارسی'),
    # ('fi', gettext_noop('Finnish')),
    ('fr', 'Français'),
    # ('fy', gettext_noop('Frisian')),
    # ('ga', gettext_noop('Irish')),
    # ('gd', gettext_noop('Scottish Gaelic')),
    # ('gl', gettext_noop('Galician')),
    # ('he', gettext_noop('Hebrew')),
    # ('hi', gettext_noop('Hindi')),
    # ('hr', gettext_noop('Croatian')),
    # ('hsb', gettext_noop('Upper Sorbian')),
    # ('hu', gettext_noop('Hungarian')),
    # ('hy', gettext_noop('Armenian')),
    # ('ia', gettext_noop('Interlingua')),
    # ('id', gettext_noop('Indonesian')),
    # ('ig', gettext_noop('Igbo')),
    # ('io', gettext_noop('Ido')),
    # ('is', gettext_noop('Icelandic')),
    ('it', 'Italiano'),
    ('ja', '日本語'),
    # ('ka', gettext_noop('Georgian')),
    # ('kab', gettext_noop('Kabyle')),
    # ('kk', gettext_noop('Kazakh')),
    # ('km', gettext_noop('Khmer')),
    # ('kn', gettext_noop('Kannada')),
    ('ko', '한국어'),
    # ('ky', gettext_noop('Kyrgyz')),
    # ('lb', gettext_noop('Luxembourgish')),
    # ('lt', gettext_noop('Lithuanian')),
    # ('lv', gettext_noop('Latvian')),
    # ('mk', gettext_noop('Macedonian')),
    # ('ml', gettext_noop('Malayalam')),
    # ('mn', gettext_noop('Mongolian')),
    # ('mr', gettext_noop('Marathi')),
    ('ms', 'Bahasa Melayu'),
    # ('my', gettext_noop('Burmese')),
    # ('nb', gettext_noop('Norwegian Bokmål')),
    # ('ne', gettext_noop('Nepali')),
    # ('nl', gettext_noop('Dutch')),
    # ('nn', gettext_noop('Norwegian Nynorsk')),
    # ('os', gettext_noop('Ossetic')),
    # ('pa', gettext_noop('Punjabi')),
    # ('pl', gettext_noop('Polish')),
    ('pt', 'Português'),
    # ('pt-br', gettext_noop('Brazilian Portuguese')),
    # ('ro', gettext_noop('Romanian')),
    ('ru', 'Русский'),
    # ('sk', gettext_noop('Slovak')),
    # ('sl', gettext_noop('Slovenian')),
    # ('sq', gettext_noop('Albanian')),
    # ('sr', gettext_noop('Serbian')),
    # ('sr-latn', gettext_noop('Serbian Latin')),
    # ('sv', gettext_noop('Swedish')),
    # ('sw', gettext_noop('Swahili')),
    # ('ta', gettext_noop('Tamil')),
    # ('te', gettext_noop('Telugu')),
    # ('tg', gettext_noop('Tajik')),
    # ('th', gettext_noop('Thai')),
    # ('tk', gettext_noop('Turkmen')),
    ('tr', gettext_noop('Turkish')),
    # ('tt', gettext_noop('Tatar')),
    # ('udm', gettext_noop('Udmurt')),
    # ('uk', gettext_noop('Ukrainian')),
    # ('ur', gettext_noop('Urdu')),
    # ('uz', gettext_noop('Uzbek')),
    # ('vi', gettext_noop('Vietnamese')),
    # ('zh-hans', gettext_noop('Simplified Chinese')),
    # ('zh-hant', gettext_noop('Traditional Chinese')),
    ('zh', '中文'),
]

# This is to stop the engine doing a SELECT postgis_version() on every request
# remember to change the version when upgrading postgis
POSTGIS_VERSION = (3, 4, 2, )
