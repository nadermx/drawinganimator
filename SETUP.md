# DjangoBase Setup Guide

This guide helps you create a new project from this Django base template.

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/djangobase.git myproject
cd myproject

# 2. Run the customization script
python customize.py

# 3. Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Set up database
python manage.py migrate
python manage.py set_languages
python manage.py createsuperuser

# 6. Run the development server
python manage.py runserver
```

## What the Customize Script Does

The `customize.py` script will prompt you for:
- **Project Name** (e.g., "MyApp") - Used in templates, emails, and admin
- **Project Domain** (e.g., "myapp.com") - Used for email sending and links
- **Database Name** (e.g., "myapp") - PostgreSQL database name

It automatically updates:
- `config.py` - All project settings
- `ansible/group_vars/all` - Deployment configuration
- Translation placeholders

## Manual Configuration Checklist

After running `customize.py`, review and update these files:

### config.py (Required)
```python
# Update these values:
PROJECT_NAME = 'YourProject'
PROJECT_DOMAIN = 'yourproject.com'
ROOT_DOMAIN = 'https://yourproject.com'  # Production URL
DEBUG = False  # Set to False in production

# Database credentials
DATABASE = {
    'default': {
        'NAME': 'yourproject',
        'USER': 'postgres',
        'PASSWORD': 'your-secure-password',
        ...
    }
}

# Payment processors (enable what you need)
PROCESSORS = ['stripe']  # Options: 'stripe', 'squareup', 'paypal', 'coinbase'

# Payment API keys
STRIPE = {
    'pk': 'pk_live_xxx',
    'sk': 'sk_live_xxx',
}

# Google Translate API (optional, for auto-translations)
GOOGLE_API = 'your-api-key'
```

### Email Setup
1. Set up Postfix on your server (see `EMAIL_SETUP.md`)
2. Configure DNS records (DKIM, SPF, DMARC)
3. Update `DEFAULT_FROM_EMAIL` in config.py

For development, use console email backend:
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

### ansible/ (For Deployment)
Copy example files and fill in your values:
```bash
cp ansible/group_vars/all.example ansible/group_vars/all
cp ansible/servers.example ansible/servers
```

Update:
- `ansible_user` - SSH user on server
- `ansible_password` - SSH password
- `githuburl` - Your repo URL
- `projectname` - Used for nginx/supervisor configs
- `domain` - Your domain
- Server IP in `servers` file

## Adding Translations

1. Go to Django admin → Translations → Text bases
2. Add new entries with unique `code_name` (e.g., `welcome_message`)
3. Run auto-translation:
   ```bash
   python manage.py run_translation
   ```
4. Use in templates:
   ```html
   {{ g.i18n.welcome_message|default:"Welcome" }}
   ```

## Setting Up Plans

Edit `finances/json/plans.json` or use Django admin:

```json
{
    "starter": {
        "code_name": "starter",
        "price": 9,
        "credits": 100,
        "days": 31,
        "subscription": true
    }
}
```

Then run:
```bash
python manage.py set_plans
```

## Payment Processor Setup

### Stripe
1. Get API keys from https://dashboard.stripe.com/apikeys
2. Add to `config.py`:
   ```python
   STRIPE = {
       'pk': 'pk_live_xxx',
       'sk': 'sk_live_xxx',
   }
   ```

### PayPal (for subscriptions)
1. Get credentials from https://developer.paypal.com
2. Add to `config.py`:
   ```python
   PAYPAL_KEYS = {
       'id': 'your-client-id',
       'secret': 'your-secret',
       'api': 'https://api.paypal.com',  # Use sandbox URL for testing
       'env': 'production',
   }
   ```
3. Run setup commands:
   ```bash
   python manage.py create_paypal_product
   python manage.py create_paypal_plans
   ```

### Square
1. Get credentials from https://developer.squareup.com
2. Add to `config.py`:
   ```python
   SQUARE_UP = {
       'env': 'production',  # or 'sandbox'
       'id': 'your-app-id',
       'secret': 'your-secret',
   }
   ```

## Customizing Templates

Key templates to customize:

| Template | Purpose |
|----------|---------|
| `templates/index.html` | Homepage |
| `templates/about.html` | About page (add your story) |
| `templates/pricing.html` | Pricing page |
| `templates/terms.html` | Terms of Service |
| `templates/privacy.html` | Privacy Policy |
| `static/css/styles.css` | Custom styles |

## Production Deployment

1. Update `config.py`:
   ```python
   DEBUG = False
   ROOT_DOMAIN = 'https://yourdomain.com'
   ```

2. Deploy with Ansible:
   ```bash
   cd ansible
   ansible-playbook -i servers djangodeployubuntu20.yml
   ```

3. Set up SSL:
   ```bash
   ansible -i servers all -m shell -a "certbot --nginx -d yourdomain.com" --become
   ```

4. Set up cron jobs:
   ```bash
   # Daily subscription billing
   0 0 * * * /home/www/myproject/venv/bin/python /home/www/myproject/manage.py rebill

   # Expire inactive subscriptions
   0 1 * * * /home/www/myproject/venv/bin/python /home/www/myproject/manage.py expire_pro_users
   ```

## File Structure Overview

```
├── accounts/         # User authentication, credits, subscriptions
├── app/              # Django settings, utilities
├── core/             # Main views (pages, checkout, auth)
├── finances/         # Payment processing
├── translations/     # Database translation system
├── templates/        # HTML templates
├── static/           # CSS, JS, images
├── ansible/          # Server deployment
├── config.py         # Your settings (gitignored)
├── config_example.py # Template for config.py
└── SETUP.md          # This file
```

## Common Commands

```bash
# Development
python manage.py runserver
python manage.py migrate
python manage.py createsuperuser

# Translations
python manage.py set_languages
python manage.py run_translation

# Plans
python manage.py set_plans

# Deployment
cd ansible && ansible-playbook -i servers gitpull.yml
```

## Troubleshooting

### Database connection error
- Check PostgreSQL is running: `sudo systemctl status postgresql`
- Verify credentials in `config.py`

### Email not sending
- Check Postfix status: `sudo systemctl status postfix`
- Test with console backend first
- Verify DNS records (SPF, DKIM, DMARC)

### Static files not loading
- Run `python manage.py collectstatic`
- Check nginx config serves `/static/` correctly

### Payment webhook errors
- Verify webhook URLs are accessible
- Check processor-specific logs in Django admin
