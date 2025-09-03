# Lightning Detection Web App

## Overview

A modern web application that displays real-time lightning strikes across Singapore on an interactive map. Built with FastAPI and based on the functionality from the existing Jupyter notebook, this app provides a user-friendly interface for monitoring lightning activity with refresh capabilities.

![Lightning Detection Web App](https://github.com/user-attachments/assets/b804995f-9ca5-4812-b503-88ea3dfb113c)

## Features

### 🌩️ Real-time Lightning Data
- Fetches data from Singapore NEA (National Environment Agency) API
- Displays lightning strikes with precise coordinates and timestamps
- Differentiates between ground strikes and cloud-to-cloud lightning

### 🗺️ Interactive Map
- Interactive Singapore map powered by Leaflet.js
- Lightning strikes marked with colored indicators
- Detailed popups with strike information
- Zoom and pan functionality

### 🔄 Refresh Functionality
- Manual refresh button for instant updates
- Automatic refresh every 5 minutes
- Real-time status indicators

### 📱 Responsive Design
- Mobile-friendly interface
- Bootstrap-based responsive layout
- Clean, professional appearance

### 🐳 Docker Support
- Complete Docker containerization
- Docker Compose for easy deployment
- Production-ready with nginx reverse proxy

## Quick Start

### Local Development

```bash
# Clone the repository
git clone https://github.com/Caisho/ura-lightning-detection.git
cd ura-lightning-detection

# Install dependencies (Python 3.10+)
pip install fastapi uvicorn jinja2 requests

# Start the application
python run.py
```

Access the application at: http://localhost:8000

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Access the application
open http://localhost:8000
```

### Production Deployment with Nginx

```bash
# Start with nginx reverse proxy
docker-compose --profile production up -d

# Access via nginx (port 80)
open http://localhost
```

## API Endpoints

### Main Interface
- `GET /` - Main web application interface

### Data APIs
- `GET /api/lightning` - Get current lightning data as JSON
- `GET /api/refresh` - Refresh data and return updated information
- `GET /api/status` - Get application status and health information

### Utility Endpoints
- `GET /health` - Simple health check
- `GET /map-only` - Get just the map HTML for embedding

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
  "timestamp": "2025-01-16T11:36:00+08:00",
  "singapore_bounds": {
    "lat_min": 0.95,
    "lat_max": 1.75,
    "lon_min": 103.27,
    "lon_max": 104.52,
    "center_lat": 1.3521,
    "center_lon": 103.8198
  }
}
```

## Architecture

### Backend (Python/FastAPI)
- **Lightning Service**: Handles NEA API communication and data processing
- **Map Generator**: Creates interactive maps with lightning markers  
- **Web Application**: FastAPI server with HTML templates and API endpoints

### Frontend (HTML/JavaScript/Bootstrap)
- **Responsive Interface**: Bootstrap-based responsive design
- **Interactive Map**: Leaflet.js integration for map functionality
- **Real-time Updates**: AJAX-based refresh functionality
- **Status Dashboard**: Live statistics and API health monitoring

### Data Flow
1. **NEA API Integration**: Fetches lightning data from Singapore government API
2. **Data Processing**: Parses and validates lightning coordinates
3. **Map Generation**: Creates interactive map with lightning markers
4. **Web Interface**: Displays data in user-friendly dashboard
5. **Auto-refresh**: Updates data every 5 minutes automatically

## Files Structure

```
lightning-detection/
├── src/
│   ├── lightning_service.py    # NEA API integration and data processing
│   ├── map_generator.py        # Interactive map generation
│   └── webapp.py              # FastAPI web application
├── templates/
│   └── index.html             # Main web interface template
├── static/                    # Static assets (CSS, JS, images)
├── notebooks/
│   └── lightning_api_test.ipynb # Original Jupyter notebook
├── Dockerfile                 # Docker container configuration
├── docker-compose.yml         # Docker Compose deployment
├── nginx.conf                 # Nginx reverse proxy configuration
├── run.py                     # Simple startup script
├── DEPLOYMENT.md              # Comprehensive deployment guide
└── pyproject.toml            # Python project configuration
```

## Configuration

### Environment Variables

```bash
# Application settings
PYTHONPATH=/app
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000

# Optional API settings
NEA_API_TIMEOUT=10
REFRESH_INTERVAL=300  # 5 minutes
```

### Port Configuration
- **Application**: 8000 (default)
- **Nginx** (production): 80
- **Health Check**: Available on application port + /health

## Deployment Options

### 1. Synology NAS Deployment

Complete instructions available in [DEPLOYMENT.md](DEPLOYMENT.md):

- Docker Package installation
- Container Manager setup (DSM 7.0+)
- Reverse proxy configuration
- Private registry setup

### 2. Cloud Deployment

- AWS ECS/Fargate ready
- Google Cloud Run compatible
- Azure Container Instances ready
- Kubernetes deployment manifests available

### 3. Self-hosted Server

- Ubuntu/CentOS compatible
- Docker and Docker Compose
- Nginx reverse proxy for SSL/TLS
- System service configuration

## Data Source

### NEA Lightning Alert API

- **Provider**: Singapore National Environment Agency (NEA)
- **Endpoint**: `https://api-open.data.gov.sg/v2/real-time/api/weather`
- **Parameter**: `api=lightning`
- **Update Frequency**: Multiple times per day during lightning activity
- **Coverage**: Singapore and surrounding areas
- **No API Key Required**: Public access for basic usage

### Lightning Types

- **Type G**: Ground lightning (red markers)
- **Type C**: Cloud-to-cloud lightning (orange markers)

## Monitoring and Maintenance

### Health Monitoring

```bash
# Check application health
curl http://localhost:8000/health

# Check detailed status
curl http://localhost:8000/api/status

# View application logs
docker logs singapore-lightning
```

### Performance Metrics

- Response time monitoring
- API availability tracking
- Error rate monitoring
- Resource usage tracking

## Development

### Adding Features

1. **New API Endpoints**: Add to `src/webapp.py`
2. **Data Processing**: Extend `src/lightning_service.py`
3. **Map Features**: Modify `src/map_generator.py`
4. **UI Updates**: Edit `templates/index.html`

### Testing

```bash
# Test lightning service
python -c "from src.lightning_service import lightning_service; print(lightning_service.get_lightning_summary())"

# Test web application
python run.py
# Then visit http://localhost:8000

# Test API endpoints
curl http://localhost:8000/api/lightning
curl http://localhost:8000/api/status
```

## Security

### Production Considerations

- **HTTPS**: Use nginx with SSL certificates
- **Rate Limiting**: Implement API rate limiting
- **Input Validation**: All inputs are validated
- **CORS**: Configured for secure cross-origin requests
- **Headers**: Security headers in nginx configuration

### Network Security

- **Firewall Rules**: Configure appropriate firewall rules
- **Network Isolation**: Use Docker networks for isolation
- **Non-root User**: Container runs as non-root user

## Troubleshooting

### Common Issues

1. **API Connection Failures**
   - Check internet connectivity
   - Verify NEA API accessibility
   - Check firewall rules

2. **Map Not Loading**
   - Verify JavaScript is enabled
   - Check CDN accessibility
   - Review browser console for errors

3. **Port Conflicts**
   - Change port in docker-compose.yml
   - Check for conflicting services
   - Use `lsof -i :8000` to check port usage

### Synology-Specific Issues

- Permission errors: Fix with `chown -R 1026:100 /volume1/docker/`
- Network issues: Enable Docker bridge network
- Resource limits: Monitor in Resource Monitor

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is part of the URA Lightning Detection system. See the main repository for license information.

## Support

For support and questions:
1. Check the troubleshooting section
2. Review application logs
3. Test API connectivity
4. Open an issue in the repository

---

**🌩️ Stay safe and monitor lightning activity in Singapore!**