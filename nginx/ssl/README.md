# SSL Certificates Setup

This directory should contain your SSL certificates for production deployment.

## Obtaining SSL Certificates

### Option 1: Let's Encrypt (Free)

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificates
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates to this directory
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./key.pem
```

### Option 2: Self-Signed (For Testing)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem -out cert.pem
```

### Option 3: Commercial Certificates

Purchase from a certificate authority and place:
- `cert.pem` - Full certificate chain
- `key.pem` - Private key

## Security Notes

- Never commit private keys to version control
- Set appropriate permissions: `chmod 600 key.pem`
- Renew certificates before expiration
