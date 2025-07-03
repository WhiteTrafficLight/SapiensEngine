#!/bin/bash

# Sapiens Engine Monitoring Script
set -e

# Configuration
APP_DIR="/opt/sapiens-engine"
DOMAIN=${DOMAIN:-"your-domain.com"}
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEMORY=85
ALERT_THRESHOLD_DISK=90

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to send alert
send_alert() {
    local message="$1"
    echo "$(date): $message" >> /var/log/sapiens-alerts.log
    
    if [ ! -z "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 ALERT: $message\"}" \
            $SLACK_WEBHOOK_URL 2>/dev/null || true
    fi
}

# Check system resources
check_system_resources() {
    print_header "System Resources"
    
    # CPU Usage
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
    if (( $(echo "$CPU_USAGE > $ALERT_THRESHOLD_CPU" | bc -l) )); then
        print_error "High CPU usage: ${CPU_USAGE}%"
        send_alert "High CPU usage detected: ${CPU_USAGE}%"
    else
        print_status "CPU usage: ${CPU_USAGE}%"
    fi
    
    # Memory Usage
    MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.1f"), $3/$2 * 100.0}')
    if (( $(echo "$MEMORY_USAGE > $ALERT_THRESHOLD_MEMORY" | bc -l) )); then
        print_error "High memory usage: ${MEMORY_USAGE}%"
        send_alert "High memory usage detected: ${MEMORY_USAGE}%"
    else
        print_status "Memory usage: ${MEMORY_USAGE}%"
    fi
    
    # Disk Usage
    DISK_USAGE=$(df / | grep -vE '^Filesystem' | awk '{print $5}' | sed 's/%//g')
    if [ $DISK_USAGE -gt $ALERT_THRESHOLD_DISK ]; then
        print_error "High disk usage: ${DISK_USAGE}%"
        send_alert "High disk usage detected: ${DISK_USAGE}%"
    else
        print_status "Disk usage: ${DISK_USAGE}%"
    fi
}

# Check Docker containers
check_docker_containers() {
    print_header "Docker Containers"
    
    cd $APP_DIR
    
    # Get container status
    CONTAINERS=$(docker-compose -f docker-compose.prod.yml ps --format "table {{.Name}}\t{{.Status}}")
    echo "$CONTAINERS"
    
    # Check if all containers are healthy
    UNHEALTHY=$(docker-compose -f docker-compose.prod.yml ps -q | xargs docker inspect --format='{{.Name}} {{.State.Health.Status}}' 2>/dev/null | grep -v healthy || true)
    
    if [ ! -z "$UNHEALTHY" ]; then
        print_error "Unhealthy containers detected:"
        echo "$UNHEALTHY"
        send_alert "Unhealthy containers detected: $UNHEALTHY"
    else
        print_status "All containers are healthy"
    fi
}

# Check application health
check_application_health() {
    print_header "Application Health"
    
    # API Health Check
    if curl -f -s https://$DOMAIN/health > /dev/null; then
        print_status "API health check passed"
    else
        print_error "API health check failed"
        send_alert "API health check failed for $DOMAIN"
    fi
    
    # Redis Health Check
    if docker exec sapiens-redis redis-cli ping | grep -q PONG; then
        print_status "Redis is responding"
    else
        print_error "Redis is not responding"
        send_alert "Redis is not responding"
    fi
    
    # Check active debate rooms
    ACTIVE_ROOMS=$(curl -s https://$DOMAIN/api/chat/debug/active-rooms | jq -r '.system_stats.total_active_rooms' 2>/dev/null || echo "0")
    MAX_ROOMS=$(curl -s https://$DOMAIN/api/chat/debug/active-rooms | jq -r '.system_stats.max_rooms' 2>/dev/null || echo "50")
    
    print_status "Active debate rooms: $ACTIVE_ROOMS/$MAX_ROOMS"
    
    if [ $ACTIVE_ROOMS -gt $((MAX_ROOMS * 8 / 10)) ]; then
        print_warning "High number of active rooms: $ACTIVE_ROOMS/$MAX_ROOMS"
    fi
}

# Check SSL certificate
check_ssl_certificate() {
    print_header "SSL Certificate"
    
    CERT_EXPIRY=$(echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -dates | grep notAfter | cut -d= -f2)
    EXPIRY_DATE=$(date -d "$CERT_EXPIRY" +%s)
    CURRENT_DATE=$(date +%s)
    DAYS_UNTIL_EXPIRY=$(( (EXPIRY_DATE - CURRENT_DATE) / 86400 ))
    
    if [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
        print_warning "SSL certificate expires in $DAYS_UNTIL_EXPIRY days"
        if [ $DAYS_UNTIL_EXPIRY -lt 7 ]; then
            send_alert "SSL certificate expires in $DAYS_UNTIL_EXPIRY days for $DOMAIN"
        fi
    else
        print_status "SSL certificate expires in $DAYS_UNTIL_EXPIRY days"
    fi
}

# Check logs for errors
check_logs() {
    print_header "Recent Errors"
    
    cd $APP_DIR
    
    # Check API logs for errors in the last hour
    RECENT_ERRORS=$(docker-compose -f docker-compose.prod.yml logs --since="1h" api | grep -i error | wc -l)
    
    if [ $RECENT_ERRORS -gt 10 ]; then
        print_warning "High number of errors in the last hour: $RECENT_ERRORS"
        docker-compose -f docker-compose.prod.yml logs --since="1h" api | grep -i error | tail -5
    else
        print_status "Error count in last hour: $RECENT_ERRORS"
    fi
}

# Generate report
generate_report() {
    print_header "System Summary"
    
    echo "Monitoring report generated at: $(date)"
    echo "Domain: $DOMAIN"
    echo "Uptime: $(uptime)"
    echo "Load average: $(uptime | awk -F'load average:' '{print $2}')"
    
    # Docker stats
    echo ""
    echo "Container resource usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
}

# Main execution
main() {
    echo -e "${BLUE}🔍 Sapiens Engine Health Check - $(date)${NC}"
    echo ""
    
    check_system_resources
    echo ""
    check_docker_containers
    echo ""
    check_application_health
    echo ""
    check_ssl_certificate
    echo ""
    check_logs
    echo ""
    generate_report
    
    echo ""
    echo -e "${GREEN}🏁 Health check completed${NC}"
}

# Run main function
main "$@" 