#!/bin/bash

# Sapiens Engine Production Deployment Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOMAIN=${DOMAIN:-"agoramind.net"}
EMAIL=${EMAIL:-"jhyu7703@gmail.com"}
APP_DIR="/opt/sapiens-engine"
BACKUP_DIR="/opt/backups"

echo -e "${GREEN}🚀 Starting Sapiens Engine Deployment${NC}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
fi

# 1. System Update and Dependencies
print_status "Updating system packages..."
apt update && apt upgrade -y

print_status "Installing Docker and Docker Compose..."
# Install Docker
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $USER
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 2. Create Application Directory
print_status "Setting up application directory..."
mkdir -p $APP_DIR
mkdir -p $BACKUP_DIR
cd $APP_DIR

# 3. Clone Repository (if not exists)
if [ ! -d ".git" ]; then
    print_status "Cloning repository..."
    git clone https://github.com/WhiteTrafficLight/SapiensEngine.git .
else
    print_status "Pulling latest changes..."
    git pull origin main
fi

# 4. Setup Environment Variables
print_status "Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp production.env.example .env
    print_warning "Please edit .env file with your actual configuration:"
    print_warning "nano .env"
    read -p "Press enter when you've configured the .env file..."
fi

# 5. Create SSL Certificate
print_status "Setting up SSL certificate..."
# Replace domain in nginx config
sed -i "s/your-domain.com/$DOMAIN/g" nginx/conf.d/sapiens.conf
sed -i "s/your-email@domain.com/$EMAIL/g" docker-compose.prod.yml

# Get initial certificate
docker-compose -f docker-compose.prod.yml run --rm certbot certonly --webroot -w /var/www/certbot --email $EMAIL -d $DOMAIN --agree-tos --no-eff-email

# 6. Deploy Services
print_status "Deploying services..."
docker-compose -f docker-compose.prod.yml up -d

# 7. Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 30

# 8. Health Check
print_status "Running health check..."
if curl -f https://$DOMAIN/health; then
    print_status "✅ Deployment successful! Service is healthy."
else
    print_error "❌ Health check failed. Check logs: docker-compose -f docker-compose.prod.yml logs"
fi

# 9. Setup SSL Certificate Renewal
print_status "Setting up SSL certificate auto-renewal..."
cat > /etc/cron.d/certbot-renew << EOF
0 12 * * * /usr/local/bin/docker-compose -f $APP_DIR/docker-compose.prod.yml run --rm certbot renew --quiet && /usr/local/bin/docker-compose -f $APP_DIR/docker-compose.prod.yml exec nginx nginx -s reload
EOF

# 10. Setup Log Rotation
print_status "Setting up log rotation..."
cat > /etc/logrotate.d/sapiens-engine << EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 appuser appuser
    postrotate
        docker-compose -f $APP_DIR/docker-compose.prod.yml restart api
    endscript
}
EOF

# 11. Firewall Configuration
print_status "Configuring firewall..."
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Your application is available at: https://$DOMAIN${NC}"
echo -e "${GREEN}📚 API Documentation: https://$DOMAIN/docs${NC}"
echo -e "${GREEN}📊 Monitoring: https://$DOMAIN:3001 (if monitoring profile enabled)${NC}"

print_status "Useful commands:"
echo "  • Check logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "  • Restart services: docker-compose -f docker-compose.prod.yml restart"
echo "  • Update application: cd $APP_DIR && git pull && docker-compose -f docker-compose.prod.yml up -d" 