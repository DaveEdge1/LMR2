#!/bin/bash
# Container Diagnostics Script
# This script helps diagnose issues with the Docker container

set -e

IMAGE_NAME="lmr2-cfr"
TAG="latest"

echo "=========================================="
echo "Docker Container Diagnostics"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
echo "1. Checking Docker installation..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "${GREEN}✓${NC} Docker is installed: ${DOCKER_VERSION}"
else
    echo -e "${RED}✗${NC} Docker is not installed"
    exit 1
fi

# Check Docker daemon
echo ""
echo "2. Checking Docker daemon..."
if docker info &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker daemon is running"
else
    echo -e "${RED}✗${NC} Docker daemon is not running"
    exit 1
fi

# Check if image exists
echo ""
echo "3. Checking if image exists..."
if docker image inspect ${IMAGE_NAME}:${TAG} &> /dev/null; then
    echo -e "${GREEN}✓${NC} Image ${IMAGE_NAME}:${TAG} exists"

    # Get image details
    IMAGE_SIZE=$(docker images ${IMAGE_NAME}:${TAG} --format "{{.Size}}")
    IMAGE_CREATED=$(docker images ${IMAGE_NAME}:${TAG} --format "{{.CreatedAt}}")
    echo "   Size: ${IMAGE_SIZE}"
    echo "   Created: ${IMAGE_CREATED}"
else
    echo -e "${YELLOW}⚠${NC} Image ${IMAGE_NAME}:${TAG} not found"
    echo "   Run 'make build' or './docker-build.sh' to build the image"
fi

# Check system resources
echo ""
echo "4. Checking system resources..."
if [ "$(uname)" == "Darwin" ]; then
    # macOS
    TOTAL_MEM=$(sysctl hw.memsize | awk '{print int($2/1024/1024/1024)" GB"}')
    echo "   Total Memory: ${TOTAL_MEM}"
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
    # Linux
    TOTAL_MEM=$(free -h | awk '/^Mem:/{print $2}')
    AVAIL_MEM=$(free -h | awk '/^Mem:/{print $7}')
    echo "   Total Memory: ${TOTAL_MEM}"
    echo "   Available Memory: ${AVAIL_MEM}"
fi

# Check Docker resources
echo ""
echo "5. Checking Docker resources..."
docker system df

# Check required files
echo ""
echo "6. Checking required files..."
FILES=("Dockerfile" "environment.yml" ".dockerignore")
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "   ${GREEN}✓${NC} ${file} exists"
    else
        echo -e "   ${RED}✗${NC} ${file} missing"
    fi
done

# Test container if image exists
if docker image inspect ${IMAGE_NAME}:${TAG} &> /dev/null; then
    echo ""
    echo "7. Testing container..."

    echo "   Testing Python..."
    if docker run --rm ${IMAGE_NAME}:${TAG} conda run -n cfr-env python --version &> /dev/null; then
        PYTHON_VERSION=$(docker run --rm ${IMAGE_NAME}:${TAG} conda run -n cfr-env python --version 2>&1)
        echo -e "   ${GREEN}✓${NC} Python accessible: ${PYTHON_VERSION}"
    else
        echo -e "   ${RED}✗${NC} Python test failed"
    fi

    echo "   Testing core packages..."
    if docker run --rm ${IMAGE_NAME}:${TAG} conda run -n cfr-env python -c "import numpy, pandas, xarray, cfr" &> /dev/null; then
        echo -e "   ${GREEN}✓${NC} Core packages import successfully"
    else
        echo -e "   ${RED}✗${NC} Core package import failed"
    fi

    echo "   Testing conda environment..."
    if docker run --rm ${IMAGE_NAME}:${TAG} conda run -n cfr-env conda list | grep -q "numpy"; then
        echo -e "   ${GREEN}✓${NC} Conda environment accessible"
    else
        echo -e "   ${RED}✗${NC} Conda environment test failed"
    fi
fi

# Network connectivity test
echo ""
echo "8. Testing network connectivity..."
if docker run --rm alpine ping -c 1 google.com &> /dev/null; then
    echo -e "   ${GREEN}✓${NC} Network connectivity OK"
else
    echo -e "   ${RED}✗${NC} Network connectivity failed"
fi

# Check for common issues
echo ""
echo "9. Checking for common issues..."

# Check disk space
if [ "$(uname)" == "Darwin" ]; then
    DISK_AVAIL=$(df -h / | awk 'NR==2 {print $4}')
    echo "   Available disk space: ${DISK_AVAIL}"
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
    DISK_AVAIL=$(df -h / | awk 'NR==2 {print $4}')
    echo "   Available disk space: ${DISK_AVAIL}"
fi

# Summary
echo ""
echo "=========================================="
echo "Diagnostics Complete"
echo "=========================================="
echo ""
echo "Recommendations:"
echo "• Ensure at least 10GB free disk space"
echo "• Allocate at least 4GB RAM to Docker"
echo "• Use BuildKit for faster builds (DOCKER_BUILDKIT=1)"
echo "• Run 'docker system prune' to free up space if needed"
echo ""
echo "For more help, see DOCKER_USAGE.md"
