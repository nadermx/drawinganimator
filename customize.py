#!/usr/bin/env python3
"""
DjangoBase Customization Script

Run this script after cloning to set up your new project.
It will prompt for project details and update all configuration files.

Usage:
    python customize.py
"""

import os
import re
import shutil
import secrets
import string


def generate_secret_key(length=50):
    """Generate a secure Django secret key."""
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(length))


def slugify(text):
    """Convert text to slug format (lowercase, underscores)."""
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def replace_in_file(filepath, replacements):
    """Replace multiple strings in a file."""
    if not os.path.exists(filepath):
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    for old, new in replacements.items():
        content = content.replace(old, new)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def main():
    print("=" * 60)
    print("DjangoBase Project Customization")
    print("=" * 60)
    print()

    # Get project details
    project_name = input("Project Name (e.g., MyApp): ").strip()
    if not project_name:
        print("Error: Project name is required")
        return

    project_domain = input("Project Domain (e.g., myapp.com): ").strip()
    if not project_domain:
        print("Error: Project domain is required")
        return

    db_name = input(f"Database Name [{slugify(project_name)}]: ").strip()
    if not db_name:
        db_name = slugify(project_name)

    db_password = input("Database Password [leave empty for random]: ").strip()
    if not db_password:
        db_password = secrets.token_urlsafe(16)
        print(f"  Generated password: {db_password}")

    use_stripe = input("Enable Stripe payments? [Y/n]: ").strip().lower() != 'n'
    use_paypal = input("Enable PayPal payments? [y/N]: ").strip().lower() == 'y'

    print()
    print("Configuration Summary:")
    print(f"  Project Name: {project_name}")
    print(f"  Domain: {project_domain}")
    print(f"  Database: {db_name}")
    print(f"  Stripe: {'Yes' if use_stripe else 'No'}")
    print(f"  PayPal: {'Yes' if use_paypal else 'No'}")
    print()

    confirm = input("Proceed with these settings? [Y/n]: ").strip().lower()
    if confirm == 'n':
        print("Cancelled.")
        return

    print()
    print("Updating configuration files...")

    # Generate Django secret key
    secret_key = generate_secret_key()

    # Build processors list
    processors = []
    if use_stripe:
        processors.append("'stripe'")
    if use_paypal:
        processors.append("'paypal'")
    processors_str = ', '.join(processors) if processors else "'stripe'"

    # 1. Create config.py from config_example.py
    if os.path.exists('config_example.py'):
        shutil.copy('config_example.py', 'config.py')

        replacements = {
            "PROJECT_NAME = 'MyProject'": f"PROJECT_NAME = '{project_name}'",
            "PROJECT_DOMAIN = 'example.com'": f"PROJECT_DOMAIN = '{project_domain}'",
            "ROOT_DOMAIN = 'http://localhost:8000'": f"ROOT_DOMAIN = 'https://{project_domain}'",
            "'NAME': 'myproject'": f"'NAME': '{db_name}'",
            "'PASSWORD': 'password'": f"'PASSWORD': '{db_password}'",
            "DEFAULT_FROM_EMAIL = 'MyProject <no-reply@example.com>'": f"DEFAULT_FROM_EMAIL = '{project_name} <no-reply@{project_domain}>'",
            "SERVER_EMAIL = 'server@example.com'": f"SERVER_EMAIL = 'server@{project_domain}'",
            "'stripe',": processors_str + ",",
        }
        replace_in_file('config.py', replacements)
        print("  ✓ Created config.py")
    else:
        print("  ✗ config_example.py not found")

    # 2. Update ansible/group_vars/all
    ansible_vars = 'ansible/group_vars/all'
    if os.path.exists(ansible_vars):
        project_slug = slugify(project_name)
        replacements = {
            'ansible_user: myproject': f'ansible_user: {project_slug}',
            'location: myproject': f'location: {project_slug}',
            'githuburl: https://github.com/yourusername/myproject.git': f'githuburl: https://github.com/yourusername/{project_slug}.git',
            'projectname: myproject': f'projectname: {project_slug}',
            'domain: myproject.com': f'domain: {project_domain}',
        }
        replace_in_file(ansible_vars, replacements)
        print("  ✓ Updated ansible/group_vars/all")

    # 3. Update ansible/disableroot.yml
    ansible_disable = 'ansible/disableroot.yml'
    if os.path.exists(ansible_disable):
        project_slug = slugify(project_name)
        replacements = {
            'newuser: myproject': f'newuser: {project_slug}',
        }
        replace_in_file(ansible_disable, replacements)
        print("  ✓ Updated ansible/disableroot.yml")

    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Create virtual environment:")
    print("     python -m venv venv && source venv/bin/activate")
    print()
    print("  2. Install dependencies:")
    print("     pip install -r requirements.txt")
    print()
    print("  3. Create PostgreSQL database:")
    print(f"     sudo -u postgres createdb {db_name}")
    print(f"     sudo -u postgres psql -c \"ALTER USER postgres PASSWORD '{db_password}';\"")
    print()
    print("  4. Run migrations:")
    print("     python manage.py migrate")
    print("     python manage.py set_languages")
    print("     python manage.py createsuperuser")
    print()
    print("  5. Start development server:")
    print("     python manage.py runserver")
    print()
    print("  6. Visit http://localhost:8000/admin to configure your site")
    print()
    print("See SETUP.md for detailed configuration instructions.")
    print()


if __name__ == '__main__':
    main()
