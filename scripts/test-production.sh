#!/bin/bash

# Test Production Environment Locally
set -e

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

# Set test domain
TEST_DOMAIN="localhost"

print_header "🧪 Testing Production Environment Locally"

# 1. Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

print_status "Docker is running"

# 2. Stop current services
print_header "Stopping current services"
docker-compose down 2>/dev/null || true

# 3. Test production build
print_header "Testing production Docker build"
if docker build -f Dockerfile.prod -t sapiens-engine:test .; then
    print_status "Production Docker build successful"
else
    print_error "Production Docker build failed"
    exit 1
fi

# 4. Create test environment
print_header "Setting up test environment"
cat > .env.test << EOF
ENVIRONMENT=production-test
REDIS_URL=redis://redis:6379
NEXTJS_SERVER_URL=http://localhost:3000
MAX_ACTIVE_ROOMS=10
MAX_MEMORY_USAGE_GB=4
MEMORY_CHECK_INTERVAL=10
PYTHONPATH=/app
PYTHONUNBUFFERED=1
EOF

# 5. Start services with production config (without nginx/ssl)
print_header "Starting services for testing"
cat > docker-compose.test.yml << EOF
services:
  redis:
    image: redis:7-alpine
    container_name: sapiens-redis-test
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_test_data:/data
    command: redis-server --appendonly yes --maxmemory 1gb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - sapiens-test-network

  api:
    image: sapiens-engine:test
    container_name: sapiens-api-test
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env.test
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - sapiens-test-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  redis_test_data:
    driver: local

networks:
  sapiens-test-network:
    driver: bridge
EOF

# Start services
docker-compose -f docker-compose.test.yml up -d

# 6. Wait for services to be ready
print_header "Waiting for services to be ready"
sleep 30

# 7. Run health checks
print_header "Running health checks"

# API Health Check
if curl -f -s http://localhost:8000/health > /dev/null; then
    print_status "API health check passed"
else
    print_error "API health check failed"
fi

# Redis Health Check
if docker exec sapiens-redis-test redis-cli ping | grep -q PONG; then
    print_status "Redis is responding"
else
    print_error "Redis is not responding"
fi

# 8. Test API endpoints
print_header "Testing API endpoints"

# Test API documentation
if curl -f -s http://localhost:8000/docs > /dev/null; then
    print_status "API documentation accessible"
else
    print_warning "API documentation not accessible"
fi

# Test debug endpoint
if curl -f -s http://localhost:8000/api/chat/debug/active-rooms > /dev/null; then
    print_status "Debug endpoint accessible"
    ACTIVE_ROOMS=$(curl -s http://localhost:8000/api/chat/debug/active-rooms | jq -r '.system_stats.total_active_rooms' 2>/dev/null || echo "0")
    print_status "Active rooms: $ACTIVE_ROOMS"
else
    print_warning "Debug endpoint not accessible"
fi

# 9. Performance test
print_header "Running performance test"
echo "Testing API response time..."
RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/health)
echo "API response time: ${RESPONSE_TIME}s"

if (( $(echo "$RESPONSE_TIME < 1.0" | bc -l) )); then
    print_status "API response time is good (< 1s)"
else
    print_warning "API response time is slow (> 1s)"
fi

# 10. Memory usage check
print_header "Checking resource usage"
echo "Container resource usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" sapiens-api-test sapiens-redis-test

# 11. Logs check
print_header "Checking logs for errors"
ERROR_COUNT=$(docker logs sapiens-api-test 2>&1 | grep -i error | wc -l)
if [ $ERROR_COUNT -eq 0 ]; then
    print_status "No errors found in logs"
else
    print_warning "Found $ERROR_COUNT errors in logs"
    echo "Recent errors:"
    docker logs sapiens-api-test 2>&1 | grep -i error | tail -3
fi

# 12. Test debate room creation (if possible)
print_header "Testing debate room creation"
ROOM_RESPONSE=$(curl -X POST -H "Content-Type: application/json" \
    -d '{"topic":"Test debate topic","user_id":"test-user","participant_limit":4}' \
    http://localhost:8000/api/chat/create-debate-room 2>/dev/null || echo "failed")

if echo "$ROOM_RESPONSE" | grep -q "room_id"; then
    print_status "Debate room creation test passed"
    ROOM_ID=$(echo "$ROOM_RESPONSE" | jq -r '.room_id' 2>/dev/null || echo "")
    if [ ! -z "$ROOM_ID" ]; then
        print_status "Created test room: $ROOM_ID"
    fi
else
    print_warning "Debate room creation test failed"
    echo "Response: $ROOM_RESPONSE"
fi

# 13. Cleanup test
print_header "Cleaning up test environment"
docker-compose -f docker-compose.test.yml down
docker volume rm sapiens_engine_redis_test_data 2>/dev/null || true
docker image rm sapiens-engine:test 2>/dev/null || true
rm -f .env.test docker-compose.test.yml

print_header "🏁 Production Test Summary"
echo -e "${GREEN}✅ Production environment test completed${NC}"
echo ""
echo "Next steps for production deployment:"
echo "1. 📦 Push code to GitHub repository"
echo "2. 🌐 Purchase domain and configure DNS"
echo "3. 🖥️  Set up production server"
echo "4. 🚀 Run deployment script on server"
echo "5. ⚙️  Configure CI/CD pipeline"
echo ""
echo -e "${BLUE}See PRODUCTION-DEPLOYMENT.md for detailed instructions${NC}" 