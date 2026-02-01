# DjangoBase

A minimal, reusable Django project template with:
- Custom user authentication (email-based)
- Credits-based billing system
- Multi-processor payments (Stripe, PayPal, Square, Coinbase)
- Database-driven translation system
- Native SMTP email (no third-party services)
- Bootstrap 5 frontend
- Redis caching and job queues

## Quick Start

```bash
# Clone and customize
git clone https://github.com/yourusername/djangobase.git myproject
cd myproject
python customize.py  # Interactive setup script

# Or manual setup
cp config_example.py config.py  # Edit with your settings

# Install dependencies
pip install -r requirements.txt

# Database
createdb myproject
python manage.py migrate
python manage.py set_languages
python manage.py createsuperuser

# Run
python manage.py runserver
```

## Configuration

Edit `config.py` with your settings:

- `PROJECT_NAME` - Your project name
- `PROJECT_DOMAIN` - Your domain (e.g., myproject.com)
- `DATABASE` - PostgreSQL connection
- `EMAIL_*` - SMTP email settings (see EMAIL_SETUP.md)
- Payment processor keys (Stripe, PayPal, Square)

See `SETUP.md` for detailed configuration instructions.

## Translation System

This project uses a custom database-driven translation system (not Django's built-in i18n).

**Setup:**
```bash
python manage.py set_languages  # Load languages from JSON
```

**Add translations:**
1. Go to Admin > Translations > Text bases
2. Add entries with `code_name` (identifier) and `text` (English)
3. Run `python manage.py run_translation` (requires Google Translate API key)

**Use in templates:**
```html
{{ g.i18n.your_code_name|default:"Fallback text" }}
```

**Use in views:**
```python
from translations.models.translation import Translation
i18n = Translation.get_text_by_lang('en')
```

## Email Setup

This template uses native SMTP email (Postfix) instead of third-party services. See `EMAIL_SETUP.md` for:
- Postfix installation and configuration
- DKIM/SPF/DMARC DNS setup
- Testing email deliverability

For development, use console backend in `config.py`:
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

## Payment Processing

Supports multiple payment processors. Configure in `config.py`:

1. **Stripe** - Credit card payments
2. **PayPal** - PayPal checkout and subscriptions
3. **Square** - Square payments
4. **Coinbase** - Cryptocurrency payments

Setup PayPal subscriptions:
```bash
python manage.py create_paypal_product
python manage.py create_paypal_plans
```

## Creating a New Project

1. Clone this template
2. Run `python customize.py` for interactive setup
3. Or manually update `config.py` with your settings
4. Customize templates in `templates/`
5. Set up email DNS records
6. Configure payment processors

## Project Structure

```
├── app/              # Django settings and main URLs
├── accounts/         # Custom user model and auth
├── core/             # Main app (views, URLs)
├── contact_messages/ # Contact form handling
├── finances/         # Payment processing
├── translations/     # Database translation system
├── templates/        # HTML templates (Bootstrap 5)
├── static/           # CSS, JS, images
├── ansible/          # Server deployment playbooks
├── customize.py      # Interactive setup script
├── SETUP.md          # Detailed setup guide
└── CLAUDE.md         # AI assistant instructions
```

## Requirements

- Python 3.10+
- PostgreSQL
- Redis
- Postfix (for email)
