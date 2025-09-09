# Lightning Detection Web App Deployment Guide

## Overview

This guide provides instructions for deploying the Singapore Lightning Detection web application using Docker containers. The application displays real-time lightning strikes on an interactive map of Singapore.

## Features

- **Real-time Lightning Data**: Fetches data from Singapore NEA API
- **Interactive Map**: Displays lightning strikes with detailed information
- **Refresh Functionality**: Manual and automatic data refresh
- **Responsive Design**: Works on desktop and mobile devices
- **Docker Support**: Easy deployment and scaling
- **Health Monitoring**: Built-in health checks and status endpoints

## Quick Start

### 1. Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/Caisho/ura-lightning-detection.git
cd ura-lightning-detection

# Build and start the application
docker-compose up -d

# Access the application
open http://localhost:8000
```

### 2. Using Docker Build

```bash
# Build the Docker image
docker build -t lightning-detection .

# Run the container
docker run -d \
  --name singapore-lightning \
  -p 8000:8000 \
  --restart unless-stopped \
  lightning-detection

# Access the application
open http://localhost:8000
```

## Production Deployment

### With Nginx Reverse Proxy

For production deployments, use the nginx profile to add a reverse proxy:

```bash
# Start with nginx reverse proxy
docker-compose --profile production up -d

# Access via nginx (port 80)
open http://localhost
```

### Environment Variables

The application supports the following environment variables:

```bash
# Application settings
PYTHONPATH=/app
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000

# Optional: Custom API settings
NEA_API_TIMEOUT=10
REFRESH_INTERVAL=300  # 5 minutes in seconds
```

## Synology NAS Deployment

### Option 1: Docker Package

1. **Install Docker Package**:
   - Open Synology Package Center
   - Search and install "Docker"

2. **Deploy via Docker Compose**:
   ```bash
   # SSH into your Synology NAS
   ssh admin@your-synology-ip
   
   # Create project directory
   mkdir -p /volume1/docker/lightning-detection
   cd /volume1/docker/lightning-detection
   
   # Download docker-compose.yml
   wget https://raw.githubusercontent.com/Caisho/ura-lightning-detection/main/docker-compose.yml
   
   # Start the application
   docker-compose up -d
   ```

3. **Access the Application**:
   - URL: `http://your-synology-ip:8000`
   - Or set up reverse proxy in Synology's Web Station

### Option 2: Container Manager (DSM 7.0+)

1. **Open Container Manager**
2. **Create Project**:
   - Name: `lightning-detection`
   - Path: `/docker/lightning-detection`
   - Source: Upload the `docker-compose.yml` file

3. **Configure Port Mapping**:
   - Container Port: `8000`
   - Local Port: `8000` (or choose another available port)

4. **Start the Project**

### Option 3: Manual Container Creation

1. **Download Docker Image**:
   ```bash
   docker pull your-registry/lightning-detection:latest
   ```

2. **Create Container**:
   - Image: `your-registry/lightning-detection:latest`
   - Container Name: `singapore-lightning`
   - Port Settings: Local `8000` → Container `8000`
   - Environment: Add variables as needed
   - Auto-restart: Enable

### Synology Reverse Proxy Setup

To access the app via domain name:

1. **Control Panel** → **Application Portal** → **Reverse Proxy**
2. **Create** new reverse proxy rule:
   - Description: `Lightning Detection`
   - Source Protocol: `HTTP`
   - Source Hostname: `your-domain.com` or `lightning.your-domain.com`
   - Source Port: `80`
   - Destination Protocol: `HTTP`
   - Destination Hostname: `localhost`
   - Destination Port: `8000`

## Container Registry

### Building and Pushing to Docker Hub

```bash
# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 \
  -t your-username/lightning-detection:latest \
  --push .
```

### Private Registry (Synology)

#### Configure Local Registry Access

First, configure Docker to work with the insecure registry on your Synology NAS:

**For Docker on Linux/macOS:**
```bash
# Edit or create Docker daemon configuration
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
  "insecure-registries": ["192.168.31.112:9500"]
}
EOF

# Restart Docker service
sudo systemctl restart docker
```

**For Docker Desktop (Windows/macOS):**
1. Open Docker Desktop settings
2. Go to **Docker Engine**
3. Add the insecure registry to the configuration:
```json
{
  "insecure-registries": ["192.168.31.112:9500"]
}
```
4. Click **Apply & Restart**

**For Synology Docker (if pushing from another container on the same NAS):**
```bash
# SSH into your Synology NAS
ssh admin@192.168.31.112

# Edit Docker daemon configuration
sudo mkdir -p /var/packages/Docker/etc
sudo tee /var/packages/Docker/etc/dockerd.json <<EOF
{
  "insecure-registries": ["192.168.31.112:9500"]
}
EOF

# Restart Docker package via Package Center or command line
sudo synoservice --restart pkgctl-Docker
```

#### Build and Push to Local Registry

```bash
# Build the image locally
docker build -t lightning-detection .

# Tag for your local Synology registry
docker tag lightning-detection:latest 192.168.31.112:9500/lightning-detection:latest

# Push to your Synology registry
docker push 192.168.31.112:9500/lightning-detection:latest

# Verify the push was successful
docker images | grep 192.168.31.112:9500
```

#### Pull and Deploy from Local Registry

```bash
# Pull from your local registry
docker pull 192.168.31.112:9500/lightning-detection:latest

# Run container from local registry image
docker run -d \
  --name singapore-lightning-local \
  -p 8000:8000 \
  --restart unless-stopped \
  192.168.31.112:9500/lightning-detection:latest
```

#### Docker Compose with Local Registry

Update your `docker-compose.yml` to use the local registry:

```yaml
version: '3.8'

services:
  lightning-webapp:
    image: 192.168.31.112:9500/lightning-detection:latest
    container_name: singapore-lightning
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### Synology Registry Setup

To set up the Docker Registry on your Synology NAS:

1. **Install Docker Registry Package**:
   - Open Package Center
   - Search for "Docker Registry"
   - Install the package

2. **Configure Registry**:
   - Open Docker Registry application
   - Configure port: `9500`
   - Enable HTTP (for local network use)
   - Set storage location: `/volume1/docker/registry`

3. **Verify Registry Access**:
   ```bash
   # Test registry connectivity
   curl http://192.168.31.112:9500/v2/_catalog
   
   # Should return: {"repositories":["lightning-detection"]}
   ```

#### Troubleshooting Registry Issues

**Common Registry Problems:**

1. **"server gave HTTP response to HTTPS client"**:
   - Ensure the registry is added to `insecure-registries`
   - Restart Docker after configuration changes

2. **Connection refused**:
   - Verify registry is running on port 9500
   - Check Synology firewall settings
   - Ensure network connectivity: `ping 192.168.31.112`

3. **Push/Pull permission denied**:
   ```bash
   # Check registry logs on Synology
   docker logs docker-registry
   
   # Verify disk space on registry volume
   df -h /volume1/docker/registry
   ```

4. **Registry cleanup** (remove old images):
   ```bash
   # SSH into Synology NAS
   ssh admin@192.168.31.112
   
   # Run registry garbage collection
   docker exec docker-registry registry garbage-collect /etc/docker/registry/config.yml
   ```