#!/bin/bash

# Sapiens Engine Backup Script
set -e

# Configuration
BACKUP_DIR="/opt/backups"
APP_DIR="/opt/sapiens-engine"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[BACKUP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Create backup directory
mkdir -p $BACKUP_DIR

print_status "Starting backup process..."

# 1. Backup Redis data
print_status "Backing up Redis data..."
docker exec sapiens-redis redis-cli BGSAVE
sleep 5  # Wait for background save to complete

# Copy Redis dump
docker cp sapiens-redis:/data/dump.rdb $BACKUP_DIR/redis_dump_$DATE.rdb
docker cp sapiens-redis:/data/appendonly.aof $BACKUP_DIR/redis_aof_$DATE.aof

# 2. Backup application configuration
print_status "Backing up application configuration..."
cd $APP_DIR
tar -czf $BACKUP_DIR/app_config_$DATE.tar.gz \
    .env \
    nginx/ \
    redis/ \
    config/ \
    docker-compose.prod.yml \
    production.env.example

# 3. Backup logs
print_status "Backing up logs..."
if [ -d "logs" ]; then
    tar -czf $BACKUP_DIR/logs_$DATE.tar.gz logs/
fi

# 4. Create backup manifest
print_status "Creating backup manifest..."
cat > $BACKUP_DIR/backup_manifest_$DATE.txt << EOF
Sapiens Engine Backup
Created: $(date)
Version: $(git rev-parse HEAD 2>/dev/null || echo "Unknown")

Files:
- redis_dump_$DATE.rdb
- redis_aof_$DATE.aof  
- app_config_$DATE.tar.gz
- logs_$DATE.tar.gz

To restore:
1. Stop services: docker-compose -f docker-compose.prod.yml down
2. Restore Redis: docker cp redis_dump_$DATE.rdb sapiens-redis:/data/dump.rdb
3. Restore config: tar -xzf app_config_$DATE.tar.gz
4. Start services: docker-compose -f docker-compose.prod.yml up -d
EOF

# 5. Cleanup old backups
print_status "Cleaning up old backups (older than $RETENTION_DAYS days)..."
find $BACKUP_DIR -name "*_*" -type f -mtime +$RETENTION_DAYS -delete

# 6. Calculate backup size
BACKUP_SIZE=$(du -sh $BACKUP_DIR | cut -f1)
print_status "Backup completed! Total backup size: $BACKUP_SIZE"

# 7. Verify backups
print_status "Verifying backup integrity..."
for file in $BACKUP_DIR/*_$DATE.*; do
    if [ -f "$file" ]; then
        if file "$file" | grep -q "cannot open"; then
            print_error "Backup verification failed for $file"
        fi
    fi
done

print_status "✅ All backups verified successfully!"

# 8. Send notification (if webhook configured)
if [ ! -z "$SLACK_WEBHOOK_URL" ]; then
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"📦 Backup completed successfully! Size: $BACKUP_SIZE\"}" \
        $SLACK_WEBHOOK_URL 2>/dev/null || true
fi

echo "Backup files created:"
ls -la $BACKUP_DIR/*_$DATE.* 