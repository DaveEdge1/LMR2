# Makefile for LMR2 Docker Container Management
# This provides simple commands to build and run the container

.PHONY: help build run shell exec clean clean-all test verify

# Configuration
IMAGE_NAME := lmr2-cfr
TAG := latest
CONTAINER_NAME := lmr2-container

# Colors for output
COLOR_RESET := \033[0m
COLOR_BOLD := \033[1m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m

help: ## Show this help message
	@echo "$(COLOR_BOLD)LMR2 Docker Container Management$(COLOR_RESET)"
	@echo ""
	@echo "$(COLOR_GREEN)Available targets:$(COLOR_RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(COLOR_YELLOW)%-15s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""

build: ## Build the Docker image
	@echo "$(COLOR_BOLD)Building Docker image: $(IMAGE_NAME):$(TAG)$(COLOR_RESET)"
	DOCKER_BUILDKIT=1 docker build -t $(IMAGE_NAME):$(TAG) .
	@echo "$(COLOR_GREEN)Build complete!$(COLOR_RESET)"

build-no-cache: ## Build the Docker image without cache
	@echo "$(COLOR_BOLD)Building Docker image without cache: $(IMAGE_NAME):$(TAG)$(COLOR_RESET)"
	DOCKER_BUILDKIT=1 docker build --no-cache -t $(IMAGE_NAME):$(TAG) .
	@echo "$(COLOR_GREEN)Build complete!$(COLOR_RESET)"

run: ## Run the container interactively with volume mounts
	@echo "$(COLOR_BOLD)Starting container...$(COLOR_RESET)"
	docker run -it --rm \
		--name $(CONTAINER_NAME) \
		-v $$(pwd)/prev_data:/app/prev_data \
		-v $$(pwd)/cases:/app/cases \
		-v $$(pwd)/recons:/app/recons \
		-e OMP_NUM_THREADS=4 \
		-e NUMEXPR_MAX_THREADS=4 \
		$(IMAGE_NAME):$(TAG)

shell: ## Start a bash shell in the container
	@echo "$(COLOR_BOLD)Starting bash shell...$(COLOR_RESET)"
	docker run -it --rm \
		--name $(CONTAINER_NAME) \
		-v $$(pwd)/prev_data:/app/prev_data \
		-v $$(pwd)/cases:/app/cases \
		-v $$(pwd)/recons:/app/recons \
		$(IMAGE_NAME):$(TAG) \
		/bin/bash -c "source /opt/conda/etc/profile.d/conda.sh && conda activate cfr-env && exec bash"

exec: ## Execute lmr_reproduce.py in the container
	@echo "$(COLOR_BOLD)Running lmr_reproduce.py...$(COLOR_RESET)"
	docker run -it --rm \
		--name $(CONTAINER_NAME) \
		-v $$(pwd)/prev_data:/app/prev_data \
		-v $$(pwd)/cases:/app/cases \
		-v $$(pwd)/recons:/app/recons \
		-e OMP_NUM_THREADS=4 \
		-e NUMEXPR_MAX_THREADS=4 \
		$(IMAGE_NAME):$(TAG) \
		conda run -n cfr-env python lmr_reproduce.py

verify: ## Verify the environment inside the container
	@echo "$(COLOR_BOLD)Verifying environment...$(COLOR_RESET)"
	docker run --rm $(IMAGE_NAME):$(TAG) conda run -n cfr-env python -c "\
import sys; \
import numpy as np; \
import pandas as pd; \
import xarray as xr; \
import netCDF4; \
import scipy; \
import matplotlib; \
import cartopy; \
import cfr; \
print('✓ All core packages imported successfully!'); \
print(f'Python: {sys.version}'); \
print(f'NumPy: {np.__version__}'); \
print(f'Pandas: {pd.__version__}'); \
print(f'xarray: {xr.__version__}'); \
print(f'CFR: {cfr.__version__}');"
	@echo "$(COLOR_GREEN)Verification complete!$(COLOR_RESET)"

test: verify ## Alias for verify

compose-up: ## Start services using docker-compose
	@echo "$(COLOR_BOLD)Starting services with docker-compose...$(COLOR_RESET)"
	docker-compose up -d
	@echo "$(COLOR_GREEN)Services started!$(COLOR_RESET)"

compose-down: ## Stop services using docker-compose
	@echo "$(COLOR_BOLD)Stopping services...$(COLOR_RESET)"
	docker-compose down
	@echo "$(COLOR_GREEN)Services stopped!$(COLOR_RESET)"

compose-logs: ## View logs from docker-compose services
	docker-compose logs -f

clean: ## Remove stopped containers and dangling images
	@echo "$(COLOR_BOLD)Cleaning up...$(COLOR_RESET)"
	docker container prune -f
	docker image prune -f
	@echo "$(COLOR_GREEN)Cleanup complete!$(COLOR_RESET)"

clean-all: ## Remove all containers, images, and volumes (CAUTION!)
	@echo "$(COLOR_YELLOW)WARNING: This will remove all Docker resources!$(COLOR_RESET)"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	docker container prune -f
	docker image prune -af
	docker volume prune -f
	docker system prune -af
	@echo "$(COLOR_GREEN)Deep cleanup complete!$(COLOR_RESET)"

info: ## Show Docker image information
	@echo "$(COLOR_BOLD)Image Information:$(COLOR_RESET)"
	@docker images $(IMAGE_NAME):$(TAG)
	@echo ""
	@echo "$(COLOR_BOLD)Image Details:$(COLOR_RESET)"
	@docker inspect $(IMAGE_NAME):$(TAG) | head -n 30

size: ## Show Docker image size
	@echo "$(COLOR_BOLD)Image Size:$(COLOR_RESET)"
	@docker images $(IMAGE_NAME):$(TAG) --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

save: ## Save the Docker image to a tar.gz file
	@echo "$(COLOR_BOLD)Saving image to $(IMAGE_NAME)-$(TAG).tar.gz...$(COLOR_RESET)"
	docker save $(IMAGE_NAME):$(TAG) | gzip > $(IMAGE_NAME)-$(TAG).tar.gz
	@echo "$(COLOR_GREEN)Image saved!$(COLOR_RESET)"
	@ls -lh $(IMAGE_NAME)-$(TAG).tar.gz

load: ## Load the Docker image from a tar.gz file
	@echo "$(COLOR_BOLD)Loading image from $(IMAGE_NAME)-$(TAG).tar.gz...$(COLOR_RESET)"
	docker load < $(IMAGE_NAME)-$(TAG).tar.gz
	@echo "$(COLOR_GREEN)Image loaded!$(COLOR_RESET)"

# Default target
.DEFAULT_GOAL := help
