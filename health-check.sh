#!/bin/bash

# Docker Health Check Script
# Quick script to verify all services are healthy

set -e

echo "========================================="
echo "Jenkins AI Chatbot - Health Check"
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ docker-compose not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ docker-compose is available${NC}"

echo ""
echo "Checking services..."
echo ""

# Check backend service
echo -n "Backend API: "
if curl -sf http://localhost:8000/api/chatbot/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Healthy${NC}"
else
    echo -e "${RED}✗ Unhealthy or not running${NC}"
fi

# Check frontend service
echo -n "Frontend: "
if curl -sf http://localhost:80/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Healthy${NC}"
else
    echo -e "${RED}✗ Unhealthy or not running${NC}"
fi

# Check Qdrant if running
echo -n "Qdrant (optional): "
if curl -sf http://localhost:6333/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Healthy${NC}"
else
    echo -e "${YELLOW}○ Not running (optional service)${NC}"
fi

# Check Redis if running
echo -n "Redis (optional): "
if docker-compose ps | grep -q "chatbot-redis.*Up"; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${YELLOW}○ Not running (optional service)${NC}"
fi

echo ""
echo "Container Status:"
docker-compose ps

echo ""
echo "========================================="
echo "Health check complete!"
echo "========================================="
