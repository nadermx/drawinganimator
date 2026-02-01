# Project Settings
PROJECT_NAME = 'Drawing Animator'
PROJECT_DOMAIN = 'drawinganimator.com'
ROOT_DOMAIN = 'https://drawinganimator.com'
DEBUG = True

# API Backend for animation processing
API_BACKEND = 'https://api.imageeditor.ai'  # or https://api.drawinganimator.com
API_KEY = ''  # API authentication key

# Google Translate API (for translations)
GOOGLE_API = ''

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # For development
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_USE_TLS = False
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
DEFAULT_FROM_EMAIL = 'Drawing Animator <no-reply@drawinganimator.com>'
SERVER_EMAIL = 'server@drawinganimator.com'

# Database
DATABASE = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'drawinganimator',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Payment Processors
PROCESSORS = [
    'stripe',
]

# Stripe
STRIPE = {
    'pk': 'pk_test_xxx',
    'sk': 'sk_test_xxx',
}

# Square (disabled by default)
SQUARE_UP = {
    'env': 'sandbox',
    'id': 'sandbox-xxx',
    'secret': 'xxx',
}

# PayPal
PAYPAL_KEYS = {
    'id': 'your-paypal-client-id',
    'secret': 'your-paypal-secret',
    'api': 'https://api.sandbox.paypal.com',
    'env': 'sandbox',
}

# Rate Limiting
RATE_LIMIT = 5  # Free tier: animations per day
RATE_LIMIT_PRO = 1000  # Pro tier: animations per day
FILES_LIMIT = 52428800  # 50MB max file size

# Animation Settings
ANIMATION_PRESETS = [
    {'id': 'walk', 'name': 'Walking', 'icon': 'bi-person-walking', 'premium': False},
    {'id': 'run', 'name': 'Running', 'icon': 'bi-person-running', 'premium': False},
    {'id': 'jump', 'name': 'Jumping', 'icon': 'bi-arrow-up-circle', 'premium': False},
    {'id': 'wave', 'name': 'Waving', 'icon': 'bi-hand-wave', 'premium': False},
    {'id': 'dance', 'name': 'Dancing', 'icon': 'bi-music-note-beamed', 'premium': False},
    {'id': 'dab', 'name': 'Dabbing', 'icon': 'bi-star', 'premium': True},
    {'id': 'zombie', 'name': 'Zombie Walk', 'icon': 'bi-person-arms-up', 'premium': True},
    {'id': 'backflip', 'name': 'Backflip', 'icon': 'bi-arrow-clockwise', 'premium': True},
]

# Script Version (for cache busting)
SCRIPT_VERSION = '1.0.0'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'error.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
