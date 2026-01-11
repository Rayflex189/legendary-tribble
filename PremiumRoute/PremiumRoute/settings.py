"""
Django settings for PremiumRoute project.
"""

import os
from pathlib import Path
import environ

# Initialize environment variables
env = environ.Env()
environ.Env.read_env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-9uhj1s#f+ss55gq7k*t9fm5v&x=zmqll=#ck-&vje!jty=8n_$')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    
    # Third party apps
    'crispy_forms',
    'crispy_bootstrap5',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'import_export',
    'django_filters',
    'django_celery_results',
    'corsheaders',
    'django_countries',
    
    # Local apps
    'accounts.apps.AccountsConfig',
    'shipping.apps.ShippingConfig',
    'consignment.apps.ConsignmentConfig',
    'tracking.apps.TrackingConfig',
    'payments.apps.PaymentsConfig',
    'notifications.apps.NotificationsConfig',
    'reports.apps.ReportsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'PremiumRoute.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'shipping.context_processors.shipping_info',
                'premiumroute.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'PremiumRoute.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# Default SQLite database (for development)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Optional: PostgreSQL for production (uncomment when needed)
# DATABASES = {
#     'default': env.db('DATABASE_URL', default='postgres://localhost/premiumroute_db')
# }


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Site ID for allauth
SITE_ID = 1

# Authentication settings
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Allauth settings
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_LOGOUT_REDIRECT_URL = '/'
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_FORMS = {
    'signup': 'accounts.forms.UserRegistrationForm',
}

LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'
LOGIN_URL = 'account_login'

# Email settings (for development use console backend)
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@premiumroute.com')

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Celery Configuration (optional, comment out if not using Celery)
# CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
# CELERY_RESULT_BACKEND = 'django-db'
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = TIME_ZONE

# Stripe Configuration (optional)
STRIPE_PUBLIC_KEY = env('STRIPE_PUBLIC_KEY', default='')
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET', default='')

# Session settings
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_NAME = 'premiumroute_sessionid'

# Cache settings (optional, for development)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'premiumroute': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Custom project settings for PremiumRoute
PREMIUMROUTE_SETTINGS = {
    'SITE_NAME': 'PremiumRoute',
    'SITE_DOMAIN': 'premiumroute.com',
    'COMPANY_NAME': 'PremiumRoute Logistics',
    'COMPANY_ADDRESS': '123 Logistics Plaza, Suite 100',
    'COMPANY_CITY': 'New York',
    'COMPANY_STATE': 'NY',
    'COMPANY_ZIP': '10001',
    'COMPANY_COUNTRY': 'US',
    'COMPANY_PHONE': '+1 (555) 123-4567',
    'COMPANY_EMAIL': 'support@premiumroute.com',
    'SUPPORT_EMAIL': 'support@premiumroute.com',
    'SALES_EMAIL': 'sales@premiumroute.com',
    'BILLING_EMAIL': 'billing@premiumroute.com',
    'DEFAULT_CURRENCY': 'USD',
    'DEFAULT_COUNTRY': 'US',
    'SHIPPING_RATES_CACHE_TIMEOUT': 3600,  # 1 hour
    'TRACKING_UPDATE_INTERVAL': 300,  # 5 minutes
    'INVOICE_PREFIX': 'PR',
    'SHIPMENT_PREFIX': 'PRSH',
    'CONSIGNMENT_PREFIX': 'PRCN',
    'PAYMENT_PREFIX': 'PRPY',
    'DEFAULT_TAX_RATE': 0.08,  # 8%
    'FREE_SHIPPING_THRESHOLD': 500.00,
    'MAX_SHIPMENT_WEIGHT': 1000,  # in kg
    'MAX_CONSIGNMENT_WEIGHT': 10000,  # in kg
}

# Security settings for production
if not DEBUG:
    # HTTPS settings
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # HSTS settings
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Cookie settings
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True
    
    # Other security settings
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# CORS settings
CORS_ALLOWED_ORIGINS = [
    'https://premiumroute.com',
    'https://www.premiumroute.com',
]

if DEBUG:
    CORS_ALLOWED_ORIGINS.extend([
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ])

CORS_ALLOW_CREDENTIALS = True

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# International shipping settings
INTERNATIONAL_SHIPPING = {
    'ALLOWED_COUNTRIES': ['US', 'CA', 'GB', 'AU', 'DE', 'FR', 'JP', 'CN', 'IN'],
    'REQUIRED_DOCUMENTS': ['commercial_invoice', 'packing_list', 'certificate_of_origin'],
    'CUSTOMS_CLEARANCE_FEE': 50.00,
    'DEFAULT_INSURANCE_RATE': 0.01,  # 1% of declared value
}

# Shipping methods and services
SHIPPING_SERVICES = {
    'STANDARD': {
        'name': 'Standard Delivery',
        'description': 'Economical shipping with standard delivery times',
        'estimated_days': '5-7 business days',
    },
    'EXPRESS': {
        'name': 'Express Delivery',
        'description': 'Fast delivery with priority handling',
        'estimated_days': '2-3 business days',
    },
    'SAME_DAY': {
        'name': 'Same Day Delivery',
        'description': 'Delivery on the same day for local shipments',
        'estimated_days': 'Same day',
    },
    'OVERNIGHT': {
        'name': 'Overnight Delivery',
        'description': 'Next business day delivery',
        'estimated_days': '1 business day',
    },
    'INTERNATIONAL': {
        'name': 'International Shipping',
        'description': 'Global shipping with customs clearance',
        'estimated_days': '7-14 business days',
    },
}