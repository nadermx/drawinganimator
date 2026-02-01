# Email Setup Guide

This project uses native SMTP email via Postfix instead of third-party services like Mailgun or SendGrid.

## Development Setup

For development, use Django's console backend to see emails in your terminal:

```python
# config.py
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

## Production Setup

### 1. Install Postfix and OpenDKIM

```bash
sudo apt-get update
sudo apt-get install postfix opendkim opendkim-tools
```

During Postfix setup, select "Internet Site" and enter your domain.

### 2. Generate DKIM Keys

```bash
# Create directory for keys
sudo mkdir -p /etc/opendkim/keys/yourdomain.com

# Generate DKIM key pair
sudo opendkim-genkey -b 2048 -d yourdomain.com -D /etc/opendkim/keys/yourdomain.com -s mail

# Set permissions
sudo chown -R opendkim:opendkim /etc/opendkim/keys
sudo chmod 600 /etc/opendkim/keys/yourdomain.com/mail.private
```

### 3. Configure OpenDKIM

Edit `/etc/opendkim.conf`:

```conf
Domain                  yourdomain.com
KeyFile                 /etc/opendkim/keys/yourdomain.com/mail.private
Selector                mail
Socket                  inet:8891@localhost
```

Edit `/etc/default/opendkim`:

```conf
SOCKET="inet:8891@localhost"
```

### 4. Configure Postfix

Edit `/etc/postfix/main.cf`:

```conf
myhostname = mail.yourdomain.com
mydomain = yourdomain.com
myorigin = $mydomain

# DKIM
milter_default_action = accept
milter_protocol = 6
smtpd_milters = inet:localhost:8891
non_smtpd_milters = inet:localhost:8891
```

### 5. Restart Services

```bash
sudo systemctl restart opendkim
sudo systemctl restart postfix
```

## DNS Records

Add these DNS records for your domain:

### A Record (for mail subdomain)
```
Type: A
Name: mail
Value: YOUR_SERVER_IP
```

### SPF Record
```
Type: TXT
Name: @
Value: v=spf1 ip4:YOUR_SERVER_IP a mx ~all
```

### DKIM Record

Get your DKIM public key:
```bash
sudo cat /etc/opendkim/keys/yourdomain.com/mail.txt
```

Add as TXT record:
```
Type: TXT
Name: mail._domainkey
Value: v=DKIM1; k=rsa; p=YOUR_PUBLIC_KEY...
```

### DMARC Record
```
Type: TXT
Name: _dmarc
Value: v=DMARC1; p=quarantine; rua=mailto:postmaster@yourdomain.com
```

### PTR Record (Reverse DNS)

Contact your hosting provider to set:
```
YOUR_SERVER_IP → mail.yourdomain.com
```

## Testing

### Check DNS Records
```bash
dig TXT yourdomain.com +short           # SPF
dig TXT mail._domainkey.yourdomain.com +short  # DKIM
dig TXT _dmarc.yourdomain.com +short    # DMARC
```

### Test DKIM Key
```bash
sudo opendkim-testkey -d yourdomain.com -s mail -vvv
```

### Send Test Email
```python
# Django shell
from app.utils import Utils
Utils.send_email(
    recipients=['your@email.com'],
    subject='Test Email',
    template='email-verification',
    data={'user': None, 'i18n': {}}
)
```

### Check Deliverability

1. Visit https://www.mail-tester.com/
2. Get a unique test email address
3. Send a test email to that address
4. Check your score (aim for 8+/10)

## Troubleshooting

### Email Not Sending
```bash
# Check Postfix status
sudo systemctl status postfix

# Check mail logs
sudo tail -f /var/log/mail.log

# Check mail queue
mailq
```

### Email Goes to Spam
1. Verify all DNS records are correct
2. Check DKIM signing: `sudo opendkim-testkey -d yourdomain.com -s mail -vvv`
3. Test with mail-tester.com
4. Ensure PTR record is set correctly

### Common Issues

- **Connection refused**: Ensure Postfix is running and listening on port 25
- **DKIM fail**: Check DKIM key in DNS matches server key
- **SPF fail**: Ensure server IP is in SPF record
- **Relay denied**: Configure Postfix to allow local relay

## Config Settings

In `config.py`:

```python
# For local Postfix
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_USE_TLS = False
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
DEFAULT_FROM_EMAIL = 'YourProject <no-reply@yourdomain.com>'
SERVER_EMAIL = 'server@yourdomain.com'
```
