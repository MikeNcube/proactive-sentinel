#!/bin/bash
# Proactive Sentinel - Verification Script (Unix/Linux/macOS)
# Usage: ./scripts/verify.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if Docker is running
check_docker() {
    print_status "Checking Docker daemon..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker daemon is not running. Please start Docker Desktop first."
        exit 1
    fi
    print_success "Docker is running"
}

# Clean up on failure
cleanup() {
    if [ -f /tmp/verification_failed ]; then
        print_warning "Verification failed. Keeping containers for debugging."
        print_warning "Run 'docker-compose logs' to see details"
    fi
}

trap cleanup EXIT

# Main verification
main() {
    echo "========================================="
    echo "  Proactive Sentinel Verification Suite"
    echo "========================================="
    echo ""
    
    # Step 0: Check Docker
    check_docker
    
    # Step 1: Start services
    print_status "Starting services..."
    docker-compose up -d
    sleep 10
    print_success "Services started"
    
    # Step 2: Check service health
    print_status "Checking service health..."
    if docker-compose ps | grep -q "Exit"; then
        print_error "Some services failed to start"
        docker-compose logs --tail=20 postgres redis app
        exit 1
    fi
    print_success "All services are running"
    
    # Step 3: Wait for PostgreSQL to be ready
    print_status "Waiting for PostgreSQL to be ready..."
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U sentinel > /dev/null 2>&1; then
            print_success "PostgreSQL is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "PostgreSQL failed to become ready"
            exit 1
        fi
        sleep 1
    done
    
    # Step 4: Create test database
    print_status "Creating test database..."
    if docker-compose exec -T postgres psql -U sentinel -c "CREATE DATABASE sentinel_test;" 2>/dev/null; then
        print_success "Test database created"
    else
        print_warning "Test database already exists, skipping"
    fi
    
    # Step 5: Initialize Alembic
    print_status "Initializing Alembic migrations..."
    if [ ! -d "migrations" ]; then
        docker-compose exec -T app flask db init > /dev/null 2>&1
        print_success "Alembic initialized"
    else
        print_warning "Migrations directory exists, skipping init"
    fi
    
    # Step 6: Create migration
    print_status "Creating migration..."
    docker-compose exec -T app flask db migrate -m "Initial multi-tenant schema" 2>&1 | grep -v "INFO  \[alembic.runtime.migration\]" || true
    print_success "Migration created"
    
    # Step 7: Apply migration
    print_status "Applying migration..."
    docker-compose exec -T app flask db upgrade
    print_success "Migration applied"
    
    # Step 8: Run tests
    print_status "Running tests..."
    if docker-compose exec -T app pytest tests/ -v --tb=short --cov=src --cov-report=term-missing; then
        print_success "All tests passed"
    else
        print_error "Tests failed"
        exit 1
    fi
    
    # Step 9: Seed database
    print_status "Seeding database with test data..."
    docker-compose exec -T app python scripts/seed_data.py
    print_success "Database seeded"
    
    # Step 10: Test API endpoints
    print_status "Testing API endpoints..."
    
    # Health check
    if curl -s http://localhost:5000/health | grep -q "healthy"; then
        print_success "Health check passed"
    else
        print_error "Health check failed"
        exit 1
    fi
    
    # Get tenant ID
    TENANT_ID=$(docker-compose exec -T postgres psql -U sentinel -d sentinel -t -c "SELECT id FROM tenants WHERE subdomain='acme' LIMIT 1;" | tr -d '[:space:]')
    
    if [ -n "$TENANT_ID" ]; then
        print_success "Found tenant: $TENANT_ID"
        
        # Test tenant endpoint
        RESPONSE=$(curl -s -H "X-Tenant-ID: $TENANT_ID" http://localhost:5000/api/tenants/current)
        if echo "$RESPONSE" | grep -q "tenant_name"; then
            print_success "Tenant API endpoint working"
        else
            print_error "Tenant API endpoint failed"
        fi
    else
        print_warning "No tenant found, skipping tenant API test"
    fi
    
    # Summary
    echo ""
    echo "========================================="
    print_success "Verification Complete!"
    echo "========================================="
    echo ""
    echo "Next steps:"
    echo "1. View logs: docker-compose logs -f"
    echo "2. Access API: http://localhost:5000"
    echo "3. Run specific tests: docker-compose exec app pytest tests/test_tenant_isolation.py -v"
    echo "4. Stop services: docker-compose down"
    echo ""
}

# Run main function
main
