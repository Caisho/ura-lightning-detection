# Synology NAS Web Demo Setup with Tailscale

This guide provides instructions for deploying the Lightning Detection web demo on a Synology NAS using Docker containers and exposing it securely via Tailscale.

## Overview

This setup allows you to:
- Host the Lightning Detection web demo on your Synology NAS
- Expose the web application securely through Tailscale
- Access the demo from anywhere with HTTPS certificates
- Maintain secure access without opening firewall ports

## Prerequisites

- Synology NAS with Docker package installed
- Tailscale account and admin access
- SSH access to your Synology NAS
- Basic Docker and networking knowledge

## Part 1: Docker Container Setup

### 1. Install Docker on Synology

1. Open **Package Center** on your Synology DSM
2. Search for and install **Docker**
3. Wait for installation to complete

### 2. Prepare Application Files

Create a directory structure on your NAS for the lightning detection demo:

```bash
# SSH into your Synology NAS
ssh your_synology_admin_username@your_nas_ip_address

# Create application directory
sudo mkdir -p /volume1/docker/lightning-demo
cd /volume1/docker/lightning-demo

# Download or copy your application files here
# Example structure:
# /volume1/docker/lightning-demo/
# ├── docker-compose.yml
# ├── Dockerfile
# ├── app/
# │   ├── index.html
# │   ├── static/
# │   └── templates/
# └── config/
```

### 3. Create Docker Compose Configuration

Create a `docker-compose.yml` file for your web demo:

```yaml
# /volume1/docker/lightning-demo/docker-compose.yml
version: '3.8'

services:
  lightning-web-demo:
    build: .
    container_name: lightning-demo
    ports:
      - "3001:3000"  # Map container port 3000 to host port 3001
    volumes:
      - ./app:/app
      - ./config:/config
      - ./data:/data
    environment:
      - NODE_ENV=production
      - PORT=3000
      - API_BASE_URL=https://api-open.data.gov.sg/v2/real-time/api/weather
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - lightning-network

networks:
  lightning-network:
    driver: bridge
```

### 4. Build and Start Container

```bash
# Navigate to your application directory
cd /volume1/docker/lightning-demo

# Build and start the container
docker-compose up -d

# Verify container is running
docker-compose ps

# Check logs
docker-compose logs -f lightning-web-demo
```

## Part 2: Tailscale Configuration

### 1. Install Tailscale on Synology

```bash
# SSH into your Synology NAS
ssh your_synology_admin_username@your_nas_ip_address

# Switch to root for installation
sudo -i

# Download and install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Start Tailscale service
tailscale up
```

Follow the authentication URL provided to connect your NAS to your Tailscale network.

### 2. Configure Tailscale Serve

Expose your Docker container through Tailscale serve:

```bash
# SSH into your Synology NAS
ssh your_synology_admin_username@your_nas_ip_address

# Switch to root
sudo -i

# Configure Tailscale to serve your application
# Replace 3001 with your actual container port
tailscale serve / http://127.0.0.1:3001 --bg
```

**Command Explanation:**
- `/` - Serve on the root path of your Tailscale hostname
- `http://127.0.0.1:3001` - Forward to your Docker container on port 3001
- `--bg` - Run in background mode

### 3. Configure HTTPS Certificate

Tailscale provides automatic HTTPS certificates via Let's Encrypt:

```bash
# Generate certificate for your Tailscale hostname
# Replace 'hostname' with your actual Tailscale device name
tailscale cert hostname.tail-scales.ts.net
```

**Certificate Details:**
- **Provider**: Let's Encrypt (free, automated)
- **Validity**: 90 days
- **Renewal**: Manual renewal required before expiry
- **Location**: Certificates stored in `/var/lib/tailscale/certs/`

### 4. Verify Configuration

```bash
# Check Tailscale serve configuration
tailscale serve status

# Test local connectivity
curl -I http://127.0.0.1:3001

# Check Tailscale status
tailscale status
```

## Part 3: Access and Testing

### 1. Access Your Web Demo

Your Lightning Detection web demo is now accessible at:
```
https://your-nas-hostname.tail-scales.ts.net
```

Where `your-nas-hostname` is your Synology NAS device name in Tailscale.

### 2. Test Functionality

1. **Basic Connectivity**: Verify the web page loads
2. **API Integration**: Test NEA Lightning API calls
3. **Interactive Maps**: Confirm map rendering works
4. **Real-time Updates**: Check if lightning data refreshes

### 3. Mobile Access

Install Tailscale on your mobile devices to access the demo from anywhere:
- iOS: Download from App Store
- Android: Download from Google Play Store
- Login with same Tailscale account

## Part 4: Certificate Management

### Certificate Renewal

Tailscale certificates expire every 90 days and require manual renewal:

```bash
# Check certificate expiry
tailscale cert --check hostname.tail-scales.ts.net

# Renew certificate before expiry
tailscale cert hostname.tail-scales.ts.net

# Restart services if needed
docker-compose restart lightning-web-demo
```

### Certificate Automation

Create a script for automated certificate renewal:

```bash
# /volume1/docker/lightning-demo/renew-cert.sh
#!/bin/bash

HOSTNAME="your-nas-hostname.tail-scales.ts.net"
LOG_FILE="/volume1/docker/lightning-demo/cert-renewal.log"

echo "$(date): Starting certificate renewal for $HOSTNAME" >> $LOG_FILE

# Renew certificate
tailscale cert $HOSTNAME >> $LOG_FILE 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): Certificate renewed successfully" >> $LOG_FILE
    # Restart container to use new certificate
    cd /volume1/docker/lightning-demo
    docker-compose restart lightning-web-demo >> $LOG_FILE 2>&1
else
    echo "$(date): Certificate renewal failed" >> $LOG_FILE
fi
```

Set up cron job for automated renewal (run monthly):

```bash
# Edit crontab
sudo crontab -e

# Add renewal job (runs on 1st of every month at 2 AM)
0 2 1 * * /volume1/docker/lightning-demo/renew-cert.sh
```

## Part 5: Management and Maintenance

### Configuration Reset

To clear Tailscale serve and funnel configurations:

```bash
# SSH into your Synology NAS
ssh your_synology_admin_username@your_nas_ip_address

# Switch to root
sudo -i

# Reset all serve and funnel configurations
tailscale serve reset
```

This command removes all active serve and funnel configurations, requiring reconfiguration.

### Container Management

```bash
# Stop the web demo
docker-compose down

# Update and restart
docker-compose pull
docker-compose up -d

# View logs
docker-compose logs -f lightning-web-demo

# Container statistics
docker stats lightning-demo
```

### Monitoring

Set up basic monitoring for your web demo:

```bash
# Create monitoring script
cat > /volume1/docker/lightning-demo/monitor.sh << 'EOF'
#!/bin/bash

# Check if container is running
if ! docker ps | grep -q lightning-demo; then
    echo "$(date): Lightning demo container is down" >> /var/log/lightning-demo.log
    # Restart container
    cd /volume1/docker/lightning-demo
    docker-compose up -d
fi

# Check if Tailscale serve is active
if ! tailscale serve status | grep -q "http://127.0.0.1:3001"; then
    echo "$(date): Tailscale serve is not active" >> /var/log/lightning-demo.log
    # Reconfigure serve
    tailscale serve / http://127.0.0.1:3001 --bg
fi
EOF

chmod +x /volume1/docker/lightning-demo/monitor.sh

# Add to crontab (check every 5 minutes)
sudo crontab -e
# Add: */5 * * * * /volume1/docker/lightning-demo/monitor.sh
```

## Part 6: Security Considerations

### Network Security

- **Tailscale Network**: Only devices in your Tailscale network can access the demo
- **No Port Forwarding**: No need to open firewall ports on your router
- **End-to-End Encryption**: All traffic encrypted via WireGuard protocol

### Access Control

```bash
# Restrict access to specific Tailscale users (optional)
tailscale serve --acl="user1@example.com,user2@example.com" / http://127.0.0.1:3001 --bg

# Enable Tailscale device authorization
tailscale up --accept-routes --accept-dns --shields-up
```

### Container Security

- Run containers with non-root user when possible
- Regularly update base images and dependencies
- Monitor container logs for suspicious activity
- Use read-only filesystems where appropriate

## Part 7: Troubleshooting

### Common Issues

**Container won't start:**
```bash
# Check Docker logs
docker-compose logs lightning-web-demo

# Verify port availability
netstat -tulpn | grep 3001

# Check file permissions
ls -la /volume1/docker/lightning-demo/
```

**Tailscale connectivity issues:**
```bash
# Check Tailscale status
tailscale status

# Restart Tailscale service
sudo systemctl restart tailscaled

# Re-authenticate if needed
tailscale up
```

**Certificate problems:**
```bash
# Check certificate validity
openssl x509 -in /var/lib/tailscale/certs/hostname.tail-scales.ts.net.crt -text -noout

# Force certificate renewal
tailscale cert --force hostname.tail-scales.ts.net
```

**Performance issues:**
```bash
# Monitor container resources
docker stats lightning-demo

# Check Synology system resources
cat /proc/meminfo
cat /proc/loadavg
```

### Support Resources

- **Tailscale Documentation**: https://tailscale.com/kb/
- **Synology Docker Guide**: DSM Help → Application → Docker
- **Container Logs**: `/volume1/docker/lightning-demo/logs/`
- **Tailscale Logs**: `journalctl -u tailscaled`

## Part 8: Advanced Configuration

### Custom Domain (Optional)

If you have a custom domain, you can configure it with Tailscale:

```bash
# Add custom domain to Tailscale
tailscale cert your-custom-domain.com

# Update serve configuration
tailscale serve --hostname=your-custom-domain.com / http://127.0.0.1:3001 --bg
```

### Load Balancing (Multiple Containers)

For high availability, run multiple container instances:

```yaml
# docker-compose.yml with multiple instances
version: '3.8'

services:
  lightning-demo-1:
    build: .
    ports:
      - "3001:3000"
    # ... other configuration

  lightning-demo-2:
    build: .
    ports:
      - "3002:3000"
    # ... other configuration

  nginx-lb:
    image: nginx:alpine
    ports:
      - "3000:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - lightning-demo-1
      - lightning-demo-2
```

## Summary

This setup provides:

✅ **Secure Web Hosting**: Lightning demo accessible via HTTPS  
✅ **Remote Access**: Available anywhere with Tailscale  
✅ **Automated Certificates**: Let's Encrypt SSL with 90-day validity  
✅ **Container Management**: Docker-based deployment on Synology  
✅ **Network Security**: No exposed ports, encrypted traffic  
✅ **Easy Maintenance**: Simple commands for management and reset  

Your Lightning Detection web demo is now securely hosted on your Synology NAS and accessible through Tailscale's encrypted network. Remember to monitor certificate expiry and renew every 90 days for continued HTTPS access.