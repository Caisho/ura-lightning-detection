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

```bash
# Tag for private registry
docker tag lightning-detection:latest your-synology:5000/lightning-detection:latest

# Push to Synology registry
docker push your-synology:5000/lightning-detection:latest
```

## Configuration

### API Settings

The application fetches data from Singapore's NEA Lightning API:
- **Endpoint**: `https://api-open.data.gov.sg/v2/real-time/api/weather`
- **Parameter**: `api=lightning`
- **Rate Limit**: No API key required for basic usage
- **Update Frequency**: Manual refresh + auto-refresh every 5 minutes

### Port Configuration

- **Default Application Port**: `8000`
- **Nginx Port** (production): `80`
- **Health Check Endpoint**: `/health`
- **API Endpoints**: `/api/lightning`, `/api/refresh`, `/api/status`

## Monitoring and Maintenance

### Health Checks

```bash
# Check application health
curl http://localhost:8000/health

# Check detailed status
curl http://localhost:8000/api/status
```

### Logs

```bash
# View application logs
docker logs singapore-lightning

# Follow logs in real-time
docker logs -f singapore-lightning

# With docker-compose
docker-compose logs -f lightning-webapp
```

### Updates

```bash
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**:
   ```bash
   # Check what's using port 8000
   lsof -i :8000
   
   # Use different port
   docker run -p 8080:8000 lightning-detection
   ```

2. **API Connection Issues**:
   - Check internet connectivity
   - Verify NEA API is accessible
   - Check firewall settings

3. **Map Not Loading**:
   - Verify JavaScript is enabled
   - Check browser console for errors
   - Ensure CDN resources are accessible

### Synology-Specific Issues

1. **Docker Permission Issues**:
   ```bash
   # Fix permissions
   sudo chown -R 1026:100 /volume1/docker/lightning-detection
   ```

2. **Network Issues**:
   - Ensure Docker bridge network is enabled
   - Check firewall rules in Security Center

3. **Resource Limits**:
   - Monitor CPU and memory usage in Resource Monitor
   - Adjust container limits if needed

## API Documentation

### Endpoints

- `GET /` - Main application interface
- `GET /api/lightning` - Get current lightning data as JSON
- `GET /api/refresh` - Refresh data and get updated information
- `GET /api/status` - Get application status
- `GET /health` - Health check endpoint
- `GET /map-only` - Get just the map HTML

### Example API Response

```json
{
  "success": true,
  "coordinates": [
    {
      "latitude": 1.3521,
      "longitude": 103.8198,
      "type": "C",
      "description": "Cloud to Cloud",
      "datetime": "2025-01-16T11:35:37+08:00"
    }
  ],
  "total_strikes": 1,
  "records_with_lightning": 1,
  "timestamp": "2025-01-16T11:36:00+08:00"
}
```

## Security Considerations

### Production Security

1. **Reverse Proxy**: Use nginx for SSL termination
2. **Network**: Run on private network when possible
3. **Updates**: Keep Docker images updated
4. **Monitoring**: Set up log monitoring and alerts

### Synology Security

1. **Firewall**: Configure firewall rules
2. **SSL/TLS**: Enable HTTPS in reverse proxy
3. **User Permissions**: Use non-admin users for Docker
4. **Network Isolation**: Use Docker networks for isolation

## Support

### Getting Help

1. **Check Logs**: Always check application logs first
2. **API Status**: Verify NEA API connectivity
3. **Network**: Test network connectivity to external services
4. **Resources**: Monitor system resources (CPU, memory, disk)

### Reporting Issues

When reporting issues, include:
- Docker version and platform
- Container logs
- System specifications
- Network configuration
- Error messages and screenshots

## License

This project is part of the URA Lightning Detection system. See the main repository for license information.