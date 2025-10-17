#!/bin/bash
# Docker Build Script for LMR2 Project
# This script provides a robust way to build the Docker container

set -e  # Exit on error

# Configuration
IMAGE_NAME="lmr2-cfr"
TAG="${1:-latest}"
DOCKERFILE="./Dockerfile"

echo "=========================================="
echo "Building Docker Image: ${IMAGE_NAME}:${TAG}"
echo "=========================================="

# Check if Dockerfile exists
if [ ! -f "$DOCKERFILE" ]; then
    echo "Error: Dockerfile not found at $DOCKERFILE"
    exit 1
fi

# Check if environment.yml exists
if [ ! -f "./environment.yml" ]; then
    echo "Error: environment.yml not found"
    exit 1
fi

# Build with BuildKit for better caching and performance
echo "Starting Docker build..."
DOCKER_BUILDKIT=1 docker build \
    --progress=plain \
    --tag "${IMAGE_NAME}:${TAG}" \
    --file "$DOCKERFILE" \
    .

# Check build status
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Build Successful!"
    echo "Image: ${IMAGE_NAME}:${TAG}"
    echo "=========================================="
    echo ""
    echo "To run the container:"
    echo "  docker run -it ${IMAGE_NAME}:${TAG}"
    echo ""
    echo "To run with mounted data directory:"
    echo "  docker run -it -v \$(pwd)/data:/app/data ${IMAGE_NAME}:${TAG}"
    echo ""
    echo "To run your script:"
    echo "  docker run -it ${IMAGE_NAME}:${TAG} conda run -n cfr-env python lmr_reproduce.py"
else
    echo ""
    echo "=========================================="
    echo "Build Failed!"
    echo "=========================================="
    exit 1
fi
