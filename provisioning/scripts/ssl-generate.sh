#!/bin/bash

#===============================================================================
# iFin Bank - SSL Certificate Generation (Development Only)
#===============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROVISIONING_DIR="$(dirname "$SCRIPT_DIR")"
SSL_DIR="$PROVISIONING_DIR/nginx/ssl"

echo "Generating self-signed SSL certificate..."
echo "WARNING: This is for development only. Use proper certificates in production!"
echo ""

mkdir -p "$SSL_DIR"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$SSL_DIR/privkey.pem" \
    -out "$SSL_DIR/fullchain.pem" \
    -subj "/C=KE/ST=Nairobi/L=Nairobi/O=iFin Bank/OU=IT/CN=localhost"

chmod 600 "$SSL_DIR/privkey.pem"
chmod 644 "$SSL_DIR/fullchain.pem"

echo ""
echo "SSL certificates generated:"
ls -la "$SSL_DIR"
echo ""
echo "Certificate details:"
openssl x509 -in "$SSL_DIR/fullchain.pem" -noout -subject -dates
