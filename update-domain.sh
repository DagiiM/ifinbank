#!/bin/bash

#===============================================================================
# Update Domain on Running Deployment
# 
# Usage: ./update-domain.sh ifinsta.com admin@email.com
#===============================================================================

set -e

DOMAIN=$1
EMAIL=$2

if [ -z "$DOMAIN" ]; then
    echo "Usage: ./update-domain.sh DOMAIN [EMAIL]"
    echo "Example: ./update-domain.sh ifinsta.com admin@example.com"
    exit 1
fi

cd provisioning

echo "Updating domain to: $DOMAIN"

# Update .env.production
if [ -f ".env.production" ]; then
    # Get current IP
    PUBLIC_IP=$(curl -s --max-time 3 ifconfig.me 2>/dev/null || echo "")
    
    # Update ALLOWED_HOSTS
    sed -i "s/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN},localhost,127.0.0.1,${PUBLIC_IP},*/" .env.production
    
    # Update CSRF_TRUSTED_ORIGINS
    sed -i "s|CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN},https://localhost|" .env.production
    
    echo "✓ Updated .env.production"
    
    # Save domain
    echo "$DOMAIN" > .domain
    
    # Update nginx config
    if [ -f "nginx/conf.d/ifinbank.conf" ]; then
        sed -i "s/server_name .*/server_name ${DOMAIN} www.${DOMAIN};/" nginx/conf.d/ifinbank.conf
        echo "✓ Updated nginx config"
    fi
    
    # Restart services to apply changes
    echo "Restarting services..."
    docker compose --env-file .env.production -f docker-compose.yml restart web nginx
    
    echo ""
    echo "✅ Domain updated successfully!"
    echo ""
    echo "Access your site at:"
    echo "  https://${DOMAIN}"
    echo "  https://www.${DOMAIN}"
    echo ""
    
    if [ -n "$EMAIL" ]; then
        echo "To setup Let's Encrypt SSL, run:"
        echo "  sudo certbot certonly --standalone -d ${DOMAIN} -d www.${DOMAIN} --email ${EMAIL}"
    fi
else
    echo "Error: .env.production not found"
    exit 1
fi
