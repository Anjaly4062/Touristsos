"""
Django settings for sosapp project.
Production and Local Development Configuration for Tourist SOS.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-lsk@wn)92zdfn6!h1o4&%xx(w%bi5q@na#nav)bu**#9u'
)

# SECURITY WARNING: don't run with debug turned on in production!
# On Render / when remote DB is configured, default to safe DEBUG=False unless explicitly set.
IS_REMOTE = bool(os.environ.get('DB_HOST') or os.environ.get('RENDER'))
if IS_REMOTE:
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')
else:
    DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'sostourist.onrender.com',
]

# Allow custom hosts from environment (e.g. Render auto-assigned domain)
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

ENV_ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS')
if ENV_ALLOWED_HOSTS:
    for host in ENV_ALLOWED_HOSTS.split(','):
        host_clean = host.strip()
        if host_clean and host_clean not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host_clean)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sosapp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'dashboard' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sosapp.wsgi.application'

# Database Configuration
if os.environ.get('DB_HOST'):
    # Production Database / Containerized Database
    raw_host = os.environ.get('DB_HOST', '').strip()
    raw_port = os.environ.get('DB_PORT', '').strip()
    db_name = os.environ.get('DB_NAME', '').strip() or 'touristsos_db'
    db_user = os.environ.get('DB_USER', '').strip() or 'tourist_user'
    db_password = os.environ.get('DB_PASSWORD', '')

    # Gracefully parse host if provided as URL or host:port
    if raw_host.startswith(('mysql://', 'mysql2://')):
        parsed = urlparse(raw_host)
        db_host = parsed.hostname or raw_host
        if parsed.port and not raw_port:
            raw_port = str(parsed.port)
        if parsed.username and not os.environ.get('DB_USER'):
            db_user = parsed.username
        if parsed.password and not os.environ.get('DB_PASSWORD'):
            db_password = parsed.password
        if parsed.path and len(parsed.path) > 1 and not os.environ.get('DB_NAME'):
            db_name = parsed.path.lstrip('/')
    elif ':' in raw_host:
        host_part, port_part = raw_host.split(':', 1)
        db_host = host_part.strip()
        if not raw_port and port_part.isdigit():
            raw_port = port_part.strip()
    else:
        db_host = raw_host

    db_port = raw_port if raw_port else '3306'

    # Determine SSL configuration:
    # Enabled for managed cloud databases (e.g. Aiven) or when explicitly requested.
    # Disabled by default for local Docker containerized MySQL (db service).
    db_ssl_env = os.environ.get('DB_SSL', '').strip().lower()
    enable_ssl = (
        db_ssl_env in ('true', '1', 'yes')
        or bool(os.environ.get('DB_SSL_CA'))
        or bool(os.environ.get('RENDER'))
        or ('aivencloud.com' in db_host)
    ) and (db_ssl_env not in ('false', '0', 'no'))

    db_options = {
        'charset': 'utf8mb4',
        'connect_timeout': 15,
    }

    if enable_ssl:
        ssl_ca_path = os.environ.get('DB_SSL_CA')
        if not ssl_ca_path:
            if os.path.exists('/etc/secrets/ca.pem'):
                ssl_ca_path = '/etc/secrets/ca.pem'
            elif (BASE_DIR / 'ca.pem').exists():
                ssl_ca_path = str(BASE_DIR / 'ca.pem')
            elif (BASE_DIR / 'ca .pem').exists():
                ssl_ca_path = str(BASE_DIR / 'ca .pem')
            else:
                ssl_ca_path = '/etc/secrets/ca.pem'

        if ssl_ca_path and os.path.exists(ssl_ca_path):
            db_options['ssl'] = {
                'ca': ssl_ca_path,
            }

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': db_name,
            'USER': db_user,
            'PASSWORD': db_password,
            'HOST': db_host,
            'PORT': db_port,
            'OPTIONS': db_options,
        }
    }
else:
    # Local Development MySQL Database
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'touristsos_db',
            'USER': 'root',
            'PASSWORD': 'Amrutha',
            'HOST': 'localhost',
            'PORT': '3306',
        }
    }

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'dashboard' / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Safe Console Logging Configuration
# Ensures uncaught exceptions and tracebacks are printed to stdout/stderr for Render logs even when DEBUG=False
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}