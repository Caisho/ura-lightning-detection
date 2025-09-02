# URA Lightning Detection

Professional subscription-based lightning alert system that provides real-time lightning detection for homes and businesses in Singapore. The system uses a centralized server that monitors NEA (National Environment Agency) Lightning Alert API and pushes alerts to subscriber hardware units when lightning is detected within their specified radius.

## Technology Stack

### Server Architecture (Python Full Stack)

**Core Framework:**
- **FastAPI + Uvicorn**: High-performance async web framework
- **SQLAlchemy + PostGIS**: Database ORM with geospatial capabilities
- **PostgreSQL**: Primary database with spatial extensions
- **Redis**: Caching, session storage, and message queuing
- **Paho-MQTT**: Hardware communication via MQTT protocol

**Web Dashboard:**
- **Vue.js 3 + TypeScript**: Modern reactive frontend framework
- **Tailwind CSS**: Utility-first styling framework
- **Chart.js**: Real-time monitoring charts and analytics
- **Leaflet.js**: Interactive Singapore maps for location management

**Monitoring & Operations:**
- **Grafana + Prometheus**: System metrics and performance dashboards
- **Sentry**: Error tracking and application monitoring
- **Celery**: Background task processing (reports, notifications)
- **Docker + Docker Compose**: Containerized deployment

### Hardware Client (Raspberry Pi)

**Prototype Device:**
- **Raspberry Pi 4 Model B**: Main computing unit with built-in WiFi/Ethernet
- **LED Alert System**: External LED connected to GPIO pin for visual lightning alerts
- **SD Card (32GB+)**: Storage for Raspberry Pi OS and client software
- **Power Supply**: Official Raspberry Pi power adapter (5V/3A)
- **Weatherproof Enclosure**: IP65-rated case for outdoor installation

**Lightweight Client Stack:**
- **Python 3.13**: Core runtime for Raspberry Pi devices
- **asyncio + aiohttp**: Async networking and HTTP clients
- **paho-mqtt**: MQTT client for server communication
- **RPi.GPIO**: Hardware control for GPIO pin and LED management
- **gpiozero**: High-level GPIO library for simplified LED control
- **systemd**: Service management and auto-restart
- **Raspberry Pi OS Lite**: Minimal operating system for optimal performance

## Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL 15+ with PostGIS extension
- Redis 7+ for caching and queuing
- MQTT broker (Mosquitto recommended)

### Raspberry Pi Hardware Setup

- **Raspberry Pi 4 Model B** (4GB RAM recommended)
- **MicroSD Card** (32GB Class 10 or higher)
- **LED and Resistor** (220Ω resistor for LED current limiting)
- **Jumper Wires** for GPIO connections
- **Breadboard** (for prototyping) or **Perfboard** (for permanent installation)
- **Weatherproof Enclosure** (IP65 rated for outdoor use)

### Raspberry Pi Software Requirements

- **Raspberry Pi OS Lite** (latest version)
- **Python 3.13** (pre-installed or via package manager)
- **GPIO libraries**: `RPi.GPIO` and `gpiozero`
- **Network connectivity**: WiFi or Ethernet configured

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Caisho/ura-lightning-detection.git
   cd ura-lightning-detection
   ```

2. **Create a virtual environment with the required Python version:**
   ```bash
   uv venv --python 3.13
   ```

3. **Activate the virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

4. **Install the project and development dependencies:**
   ```bash
   uv sync --extra dev
   ```

5. **Setup infrastructure services:**
   ```bash
   # Start PostgreSQL, Redis, and MQTT broker
   docker-compose up -d postgres redis mosquitto
   
   # Initialize database with PostGIS
   python scripts/init_database.py
   ```

6. **Setup Raspberry Pi prototype (optional for testing):**
   ```bash
   # Install Raspberry Pi GPIO libraries (Linux only)
   pip install RPi.GPIO gpiozero
   
   # For development on non-Raspberry Pi systems, use GPIO simulator
   pip install gpiozero[mock]
   ```

## Development

After setup, you can:

- **Run server**: `uvicorn src.main:app --reload`
- **Run tests**: `pytest`
- **Format code**: `ruff format`
- **Lint code**: `ruff check`
- **Check for dead code**: `vulture src/`
- **Run frontend**: `npm run dev` (in `web/` directory)
- **Test Raspberry Pi client**: `python hardware/lightning_client.py hw_test_device localhost`
- **Simulate GPIO on development machine**: `GPIOZERO_PIN_FACTORY=mock python hardware/lightning_client.py`

## Full Stack Architecture

### Server Application Structure

```python
# src/main.py - FastAPI application entry point
from fastapi import FastAPI, WebSocket, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from .api import lightning, customers, hardware, monitoring
from .services import nea_api, alert_processor, mqtt_publisher
from .database import database, models

app = FastAPI(title="Lightning Alert System", version="1.0.0")

# Background task for NEA API monitoring
@app.on_event("startup")
async def startup_event():
    await database.connect()
    asyncio.create_task(nea_api.monitor_lightning_continuously())

# RESTful API endpoints
app.include_router(lightning.router, prefix="/api/lightning")
app.include_router(customers.router, prefix="/api/customers")
app.include_router(hardware.router, prefix="/api/hardware")
app.include_router(monitoring.router, prefix="/api/monitoring")

# WebSocket for real-time dashboard updates
@app.websocket("/ws/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    await websocket.accept()
    # Stream real-time alerts and system status
```

### Database Schema (PostgreSQL + PostGIS)

```sql
-- Enable PostGIS for spatial operations
CREATE EXTENSION IF NOT EXISTS postgis;

-- Customer management
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    subscription_tier VARCHAR(20) NOT NULL,
    subscription_status VARCHAR(20) DEFAULT 'active' CHECK (subscription_status IN ('active', 'inactive', 'suspended', 'cancelled')),
    joined_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Separate subscription tracking table for better audit trail
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    subscription_type VARCHAR(10) NOT NULL CHECK (subscription_type IN ('monthly', 'annual')),
    started_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'cancelled', 'renewed')),
    billing_amount DECIMAL(10,2),
    billing_currency VARCHAR(3) DEFAULT 'SGD',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Payment tracking (minimal sensitive data)
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE CASCADE,
    payment_status VARCHAR(20) NOT NULL CHECK (payment_status IN ('pending', 'completed', 'failed', 'refunded')),
    payment_method VARCHAR(20), -- 'credit_card', 'bank_transfer', etc.
    payment_reference VARCHAR(100), -- External payment gateway reference
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'SGD',
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Hardware devices with geographic locations and Singapore addresses
CREATE TABLE hardware_units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    device_id VARCHAR(50) UNIQUE NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    device_name VARCHAR(100), -- User-friendly name like "Home - Garden", "Office - Rooftop"
    
    -- Geographic coordinates (required for alerts)
    location GEOGRAPHY(POINT, 4326) NOT NULL,  -- PostGIS geographic point
    
    -- Singapore physical address (required for service/support)
    address_line_1 VARCHAR(200) NOT NULL,
    address_line_2 VARCHAR(200),
    postal_code VARCHAR(6) NOT NULL, -- Singapore postal codes are 6 digits
    building_name VARCHAR(100),
    unit_number VARCHAR(20),
    
    -- Alert configuration
    alert_radius_km INTEGER NOT NULL DEFAULT 8,
    
    -- Device status and monitoring
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance', 'decommissioned')),
    last_seen TIMESTAMP,
    firmware_version VARCHAR(20),
    installation_date DATE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Spatial index for fast proximity queries
CREATE INDEX idx_hardware_location ON hardware_units USING GIST(location);

-- Customer management indexes
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_subscription_status ON customers(subscription_status);
CREATE INDEX idx_customers_joined ON customers(joined_at);

-- Subscription management indexes
CREATE INDEX idx_subscriptions_customer_id ON subscriptions(customer_id);
CREATE INDEX idx_subscriptions_expires_at ON subscriptions(expires_at);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_started_at ON subscriptions(started_at);

-- Payment tracking indexes
CREATE INDEX idx_payments_subscription_id ON payments(subscription_id);
CREATE INDEX idx_payments_status ON payments(payment_status);
CREATE INDEX idx_payments_paid_at ON payments(paid_at);

-- Hardware management indexes
CREATE INDEX idx_hardware_customer_id ON hardware_units(customer_id);
CREATE INDEX idx_hardware_postal_code ON hardware_units(postal_code);
CREATE INDEX idx_hardware_status ON hardware_units(status);

-- Lightning strikes log for analytics
CREATE TABLE lightning_strikes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strike_location GEOGRAPHY(POINT, 4326) NOT NULL,
    strike_time TIMESTAMP NOT NULL,
    lightning_type VARCHAR(10),
    detected_at TIMESTAMP DEFAULT NOW()
);

-- Alert history for customer analytics
CREATE TABLE alert_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hardware_id UUID REFERENCES hardware_units(id),
    strike_id UUID REFERENCES lightning_strikes(id),
    distance_km DECIMAL(5,2),
    alert_sent_at TIMESTAMP DEFAULT NOW(),
    alert_level VARCHAR(20)
);
```

### Core Services Architecture

```python
# src/services/nea_api.py - NEA API monitoring service
import asyncio
import aiohttp
from typing import List
from ..models.lightning import LightningStrike

class NEAApiService:
    def __init__(self):
        self.api_url = "https://api.data.gov.sg/v1/environment/lightning"
        self.poll_interval = 30  # seconds
        
    async def monitor_lightning_continuously(self):
        """Continuously monitor NEA API for new lightning strikes"""
        while True:
            try:
                strikes = await self.fetch_lightning_data()
                if strikes:
                    await self.process_new_strikes(strikes)
            except Exception as e:
                logger.error(f"NEA API error: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def fetch_lightning_data(self) -> List[LightningStrike]:
        """Fetch latest lightning data from NEA API"""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.api_url) as response:
                data = await response.json()
                return self.parse_lightning_data(data)

# src/services/alert_processor.py - Geographic alert processing
from sqlalchemy import text
from ..database.database import database

class AlertProcessor:
    async def process_lightning_strike(self, strike: LightningStrike):
        """Find affected customers and send targeted alerts"""
        
        # Use PostGIS for efficient spatial query
        query = text("""
            SELECT 
                h.device_id,
                h.customer_id,
                ST_Distance(h.location, ST_SetSRID(ST_Point(:lon, :lat), 4326)) / 1000 as distance_km,
                h.alert_radius_km,
                c.subscription_tier
            FROM hardware_units h
            JOIN customers c ON h.customer_id = c.id
            WHERE h.status = 'active'
            AND ST_DWithin(
                h.location, 
                ST_SetSRID(ST_Point(:lon, :lat), 4326), 
                h.alert_radius_km * 1000
            )
        """)
        
        affected_devices = await database.fetch_all(
            query, values={
                "lat": strike.latitude, 
                "lon": strike.longitude
            }
        )
        
        # Send alerts only to affected devices
        for device in affected_devices:
            await self.send_alert_to_device(device, strike)

# src/services/mqtt_publisher.py - Hardware communication
import json
import paho.mqtt.client as mqtt
from ..models.alerts import LightningAlert

class MQTTPublisher:
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.client = mqtt.Client()
        self.client.connect(broker_host, broker_port, 60)
        self.client.loop_start()
    
    async def send_lightning_alert(self, device_id: str, alert: LightningAlert):
        """Send alert to specific hardware device via MQTT"""
        topic = f"lightning/alerts/{device_id}"
        message = {
            "command": "LIGHTNING_ALERT",
            "alert_id": alert.id,
            "timestamp": alert.timestamp.isoformat(),
            "lightning_data": {
                "distance_km": alert.distance_km,
                "strike_time": alert.strike_time.isoformat(),
                "strike_location": {
                    "latitude": alert.strike_latitude,
                    "longitude": alert.strike_longitude
                }
            },
            "alert_level": alert.level
        }
        
        self.client.publish(topic, json.dumps(message), qos=1)
```

### Subscription Management Queries

```python
# src/services/subscription_service.py - Subscription management
from datetime import datetime, timedelta
from sqlalchemy import text
from ..database.database import database

class SubscriptionService:
    async def check_expiring_subscriptions(self, days_ahead: int = 7):
        """Find subscriptions expiring within specified days"""
        expiry_date = datetime.now() + timedelta(days=days_ahead)
        
        query = text("""
            SELECT id, email, subscription_tier, subscription_type, 
                   subscription_expires_at, payment_status
            FROM customers 
            WHERE subscription_expires_at <= :expiry_date
            AND subscription_expires_at > NOW()
            AND payment_status = 'active'
            ORDER BY subscription_expires_at ASC
        """)
        
        return await database.fetch_all(query, values={"expiry_date": expiry_date})
    
    async def get_overdue_customers(self):
        """Find customers with overdue payments"""
        query = text("""
            SELECT id, email, subscription_tier, subscription_expires_at, 
                   EXTRACT(DAYS FROM (NOW() - subscription_expires_at)) as days_overdue
            FROM customers 
            WHERE subscription_expires_at < NOW()
            AND payment_status IN ('active', 'overdue')
            ORDER BY subscription_expires_at ASC
        """)
        
        return await database.fetch_all(query)
    
    async def update_payment_status(self, customer_id: str, status: str):
        """Update customer payment status"""
        query = text("""
            UPDATE customers 
            SET payment_status = :status,
                updated_at = NOW()
            WHERE id = :customer_id
            RETURNING id, payment_status
        """)
        
        return await database.fetch_one(
            query, 
            values={"customer_id": customer_id, "status": status}
        )
    
    async def get_subscription_analytics(self):
        """Get subscription analytics for business intelligence"""
        query = text("""
            SELECT 
                subscription_tier,
                subscription_type,
                payment_status,
                COUNT(*) as customer_count,
                AVG(EXTRACT(DAYS FROM (subscription_expires_at - subscription_started_at))) as avg_subscription_length_days,
                SUM(CASE WHEN payment_status = 'active' THEN 1 ELSE 0 END) as active_count,
                SUM(CASE WHEN payment_status IN ('overdue', 'suspended') THEN 1 ELSE 0 END) as problem_count
            FROM customers
            GROUP BY subscription_tier, subscription_type, payment_status
            ORDER BY subscription_tier, subscription_type, payment_status
        """)
        
        return await database.fetch_all(query)
    
    async def renew_subscription(self, customer_id: str, months: int = 12):
        """Renew customer subscription and reset payment status"""
        query = text("""
            UPDATE customers 
            SET subscription_started_at = NOW(),
                subscription_expires_at = NOW() + INTERVAL ':months months',
                payment_status = 'active',
                updated_at = NOW()
            WHERE id = :customer_id
            RETURNING id, subscription_started_at, subscription_expires_at
        """)
        
        return await database.fetch_one(
            query, 
            values={"customer_id": customer_id, "months": months}
        )
    
    async def suspend_non_paying_customers(self):
        """Suspend hardware for customers with payment issues"""
        # First mark overdue customers
        await database.execute(text("""
            UPDATE customers 
            SET payment_status = 'overdue'
            WHERE subscription_expires_at < NOW() - INTERVAL '3 days'
            AND payment_status = 'active'
        """))
        
        # Then suspend customers overdue for more than 7 days
        await database.execute(text("""
            UPDATE customers 
            SET payment_status = 'suspended'
            WHERE subscription_expires_at < NOW() - INTERVAL '7 days'
            AND payment_status = 'overdue'
        """))
        
        # Deactivate hardware for suspended customers
        query = text("""
            UPDATE hardware_units 
            SET status = 'inactive'
            WHERE customer_id IN (
                SELECT id FROM customers 
                WHERE payment_status IN ('suspended', 'cancelled')
            )
            AND status = 'active'
            RETURNING device_id, customer_id
        """)
        
        return await database.fetch_all(query)
    
    async def reactivate_customer(self, customer_id: str):
        """Reactivate customer after payment received"""
        # Update customer status
        await self.update_payment_status(customer_id, 'active')
        
        # Reactivate their hardware
        query = text("""
            UPDATE hardware_units 
            SET status = 'active'
            WHERE customer_id = :customer_id
            AND status = 'inactive'
            RETURNING device_id
        """)
        
        return await database.fetch_all(query, values={"customer_id": customer_id})
```

### Hardware Client Implementation (Raspberry Pi)

```python
# hardware/lightning_client.py - Raspberry Pi client with LED control
import asyncio
import json
import logging
import sys
from threading import Timer
import paho.mqtt.client as mqtt

# GPIO library imports with fallback for development
try:
    from gpiozero import LED
    GPIO_AVAILABLE = True
except ImportError:
    # Fallback for development on non-Raspberry Pi systems
    print("GPIO libraries not available - using mock mode")
    from unittest.mock import MagicMock
    LED = MagicMock
    GPIO_AVAILABLE = False

class LightningAlertHardware:
    def __init__(self, device_id: str, mqtt_broker: str, led_pin: int = 18):
        self.device_id = device_id
        self.mqtt_broker = mqtt_broker
        self.alert_active = False
        self.clear_timer = None
        self.alert_timeout = 30 * 60  # 30 minutes
        
        # GPIO setup for LED control
        if GPIO_AVAILABLE:
            self.led = LED(led_pin)
            logging.info(f"LED initialized on GPIO pin {led_pin}")
        else:
            self.led = LED()  # Mock LED for development
            logging.info("Using mock LED for development")
        
        # MQTT setup
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_alert_received
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        # Blinking task control
        self.blink_task = None
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    async def start(self):
        """Start the hardware client"""
        try:
            self.mqtt_client.connect(self.mqtt_broker, 1883, 60)
            self.mqtt_client.loop_forever()
        except Exception as e:
            logging.error(f"Failed to connect to MQTT broker: {e}")
            # Retry connection after 30 seconds
            await asyncio.sleep(30)
            await self.start()
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """Subscribe to device-specific alert topic"""
        if rc == 0:
            topic = f"lightning/alerts/{self.device_id}"
            client.subscribe(topic, qos=1)
            logging.info(f"Connected to MQTT broker, subscribed to {topic}")
            
            # Subscribe to system commands
            client.subscribe(f"lightning/commands/{self.device_id}", qos=1)
            
            # Send heartbeat to server
            self.send_heartbeat()
        else:
            logging.error(f"MQTT connection failed with code {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection"""
        logging.warning(f"MQTT disconnected with code {rc}")
        if rc != 0:
            logging.info("Attempting to reconnect...")
    
    def on_alert_received(self, client, userdata, message):
        """Handle incoming lightning alert or system commands"""
        try:
            topic = message.topic
            payload = json.loads(message.payload.decode())
            
            if "alerts" in topic and payload.get("command") == "LIGHTNING_ALERT":
                self.process_lightning_alert(payload)
            elif "commands" in topic:
                self.process_system_command(payload)
                
        except Exception as e:
            logging.error(f"Error processing message: {e}")
    
    def process_lightning_alert(self, alert_data):
        """Process incoming lightning alert"""
        alert_id = alert_data.get('alert_id', 'unknown')
        distance = alert_data.get('lightning_data', {}).get('distance_km', 0)
        
        logging.info(f"Lightning alert received: {alert_id}, distance: {distance}km")
        
        self.activate_visual_alerts()
        self.reset_clear_timer()
        
        # Send acknowledgment back to server
        self.send_alert_acknowledgment(alert_id)
    
    def process_system_command(self, command_data):
        """Process system commands like test alerts or configuration updates"""
        command = command_data.get("command")
        
        if command == "TEST_ALERT":
            logging.info("Test alert command received")
            self.activate_visual_alerts()
            # Test alerts clear after 10 seconds
            Timer(10, self.clear_test_alert).start()
            
        elif command == "CLEAR_ALERT":
            logging.info("Clear alert command received")
            self.clear_alert_immediately()
            
        elif command == "STATUS_REQUEST":
            logging.info("Status request received")
            self.send_status_report()
    
    def activate_visual_alerts(self):
        """Turn on LED alerts with blinking pattern"""
        if not self.alert_active:
            self.alert_active = True
            self.start_led_blinking()
            logging.info("Visual alerts activated - LED blinking started")
    
    def start_led_blinking(self):
        """Start LED blinking pattern at 1Hz"""
        if self.blink_task:
            self.blink_task.cancel()
        
        self.blink_task = asyncio.create_task(self._blink_led())
    
    async def _blink_led(self):
        """Async LED blinking coroutine"""
        try:
            while self.alert_active:
                self.led.on()
                await asyncio.sleep(0.5)
                self.led.off()
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            self.led.off()
            logging.info("LED blinking stopped")
    
    def reset_clear_timer(self):
        """Reset the 30-minute auto-clear timer"""
        if self.clear_timer:
            self.clear_timer.cancel()
        
        self.clear_timer = Timer(self.alert_timeout, self.auto_clear_alert)
        self.clear_timer.start()
        logging.info("Alert timer reset to 30 minutes")
    
    def auto_clear_alert(self):
        """Automatically clear alerts after 30 minutes"""
        self.clear_alert_immediately()
        logging.info("Alert automatically cleared after 30 minutes")
    
    def clear_test_alert(self):
        """Clear test alerts after 10 seconds"""
        if self.alert_active:
            self.clear_alert_immediately()
            logging.info("Test alert cleared after 10 seconds")
    
    def clear_alert_immediately(self):
        """Immediately clear all alerts"""
        self.alert_active = False
        
        if self.blink_task:
            self.blink_task.cancel()
            self.blink_task = None
        
        if self.clear_timer:
            self.clear_timer.cancel()
            self.clear_timer = None
        
        self.led.off()
        logging.info("All alerts cleared")
    
    def send_heartbeat(self):
        """Send periodic heartbeat to server"""
        heartbeat_data = {
            "device_id": self.device_id,
            "timestamp": asyncio.get_event_loop().time(),
            "status": "online",
            "alert_active": self.alert_active,
            "gpio_available": GPIO_AVAILABLE
        }
        
        topic = f"lightning/heartbeat/{self.device_id}"
        self.mqtt_client.publish(topic, json.dumps(heartbeat_data), qos=1)
        
        # Schedule next heartbeat in 5 minutes
        Timer(300, self.send_heartbeat).start()
    
    def send_alert_acknowledgment(self, alert_id: str):
        """Send acknowledgment that alert was received and processed"""
        ack_data = {
            "device_id": self.device_id,
            "alert_id": alert_id,
            "timestamp": asyncio.get_event_loop().time(),
            "status": "acknowledged"
        }
        
        topic = f"lightning/acknowledgments/{self.device_id}"
        self.mqtt_client.publish(topic, json.dumps(ack_data), qos=1)
    
    def send_status_report(self):
        """Send detailed status report to server"""
        status_data = {
            "device_id": self.device_id,
            "timestamp": asyncio.get_event_loop().time(),
            "system_status": {
                "alert_active": self.alert_active,
                "gpio_available": GPIO_AVAILABLE,
                "timer_active": self.clear_timer is not None,
                "blink_task_active": self.blink_task is not None and not self.blink_task.done()
            }
        }
        
        topic = f"lightning/status/{self.device_id}"
        self.mqtt_client.publish(topic, json.dumps(status_data), qos=1)

# Hardware startup script with command line configuration
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lightning_client.py <device_id> [mqtt_broker] [led_pin]")
        print("Example: python lightning_client.py hw_garden_001 localhost 18")
        sys.exit(1)
    
    device_id = sys.argv[1]
    mqtt_broker = sys.argv[2] if len(sys.argv) > 2 else "localhost"
    led_pin = int(sys.argv[3]) if len(sys.argv) > 3 else 18
    
    if not GPIO_AVAILABLE:
        print("Warning: Running in development mode without GPIO access")
        print("Install RPi.GPIO and gpiozero on Raspberry Pi for full functionality")
    
    hardware = LightningAlertHardware(device_id, mqtt_broker, led_pin)
    
    try:
        asyncio.run(hardware.start())
    except KeyboardInterrupt:
        logging.info("Lightning client stopped by user")
        hardware.clear_alert_immediately()
    except Exception as e:
        logging.error(f"Lightning client error: {e}")
```

### Raspberry Pi Hardware Wiring

```
Raspberry Pi GPIO Wiring for LED Alert:

GPIO Pin 18 (Physical Pin 12) ──── 220Ω Resistor ──── LED Anode (+)
                                                       |
Ground (Physical Pin 6) ─────────────────────────── LED Cathode (-)

Alternative GPIO pins: 2, 3, 4, 17, 27, 22, 10, 9, 11, 5, 6, 13, 19, 26
```

### Raspberry Pi Installation Script

```bash
#!/bin/bash
# install_raspberry_pi.sh - Automated setup for Raspberry Pi lightning client

echo "Lightning Alert System - Raspberry Pi Setup"
echo "==========================================="

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.13 and development tools
sudo apt install -y python3.13 python3.13-venv python3.13-dev python3-pip

# Install GPIO libraries
sudo apt install -y python3-rpi.gpio python3-gpiozero

# Create application directory
sudo mkdir -p /opt/lightning-alert
sudo chown pi:pi /opt/lightning-alert
cd /opt/lightning-alert

# Download client software
wget https://github.com/Caisho/ura-lightning-detection/releases/latest/download/raspberry-pi-client.tar.gz
tar -xzf raspberry-pi-client.tar.gz

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/lightning-alert.service > /dev/null <<EOF
[Unit]
Description=Lightning Alert Hardware Client
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/opt/lightning-alert
Environment=PATH=/opt/lightning-alert/venv/bin
ExecStart=/opt/lightning-alert/venv/bin/python hardware/lightning_client.py DEVICE_ID_HERE mqtt.yourdomain.com
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable lightning-alert.service

echo "Setup complete! Configure your device ID and MQTT broker, then start with:"
echo "sudo systemctl start lightning-alert.service"
```

### Web Dashboard (Vue.js)

```typescript
// web/src/components/LightningMonitor.vue
<template>
  <div class="lightning-monitor">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <!-- Real-time status -->
      <div class="bg-white p-6 rounded-lg shadow">
        <h3 class="text-lg font-semibold mb-4">System Status</h3>
        <div class="space-y-2">
          <div class="flex justify-between">
            <span>Active Devices:</span>
            <span class="font-mono">{{ stats.activeDevices }}</span>
          </div>
          <div class="flex justify-between">
            <span>Alerts Today:</span>
            <span class="font-mono">{{ stats.alertsToday }}</span>
          </div>
          <div class="flex justify-between">
            <span>API Status:</span>
            <span class="font-mono text-green-600">Connected</span>
          </div>
        </div>
      </div>
      
      <!-- Live lightning map -->
      <div class="md:col-span-2 bg-white p-6 rounded-lg shadow">
        <h3 class="text-lg font-semibold mb-4">Live Lightning Activity</h3>
        <div id="lightning-map" class="h-64"></div>
      </div>
    </div>
    
    <!-- Recent alerts table -->
    <div class="mt-6 bg-white rounded-lg shadow">
      <RecentAlertsTable :alerts="recentAlerts" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import L from 'leaflet'
import RecentAlertsTable from './RecentAlertsTable.vue'

interface LightningAlert {
  id: string
  timestamp: string
  location: { latitude: number; longitude: number }
  affectedDevices: number
  distance: number
}

const stats = ref({
  activeDevices: 0,
  alertsToday: 0,
  apiStatus: 'connected'
})

const recentAlerts = ref<LightningAlert[]>([])
let map: L.Map
let websocket: WebSocket

onMounted(() => {
  initializeMap()
  connectWebSocket()
})

function initializeMap() {
  // Initialize Leaflet map centered on Singapore
  map = L.map('lightning-map').setView([1.3521, 103.8198], 11)
  
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map)
}

function connectWebSocket() {
  websocket = new WebSocket('ws://localhost:8000/ws/monitoring')
  
  websocket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    if (data.type === 'lightning_alert') {
      addLightningStrike(data.strike)
      recentAlerts.value.unshift(data)
      if (recentAlerts.value.length > 50) {
        recentAlerts.value = recentAlerts.value.slice(0, 50)
      }
    }
    
    if (data.type === 'stats_update') {
      stats.value = data.stats
    }
  }
}

function addLightningStrike(strike: any) {
  // Add lightning strike marker to map
  const marker = L.circleMarker([strike.latitude, strike.longitude], {
    radius: 8,
    fillColor: '#ff7800',
    color: '#000',
    weight: 1,
    opacity: 1,
    fillOpacity: 0.8
  }).addTo(map)
  
  // Remove marker after 10 minutes
  setTimeout(() => {
    map.removeLayer(marker)
  }, 10 * 60 * 1000)
}

onUnmounted(() => {
  if (websocket) {
    websocket.close()
  }
})
</script>
```

### Deployment Configuration

```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgis/postgis:15-3.3
    environment:
      POSTGRES_DB: lightning_alerts
      POSTGRES_USER: lightning_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  mosquitto:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./config/mosquitto.conf:/mosquitto/config/mosquitto.conf

  lightning-server:
    build: .
    environment:
      DATABASE_URL: postgresql://lightning_user:${POSTGRES_PASSWORD}@postgres/lightning_alerts
      REDIS_URL: redis://redis:6379
      MQTT_BROKER: mosquitto
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - mosquitto

  web-dashboard:
    build: ./web
    ports:
      - "3000:3000"
    depends_on:
      - lightning-server

  # Optional: Raspberry Pi simulator for testing without hardware
  pi-simulator:
    build: ./hardware
    environment:
      DEVICE_ID: "sim_test_device"
      MQTT_BROKER: mosquitto
      GPIO_MOCK: "true"
    depends_on:
      - mosquitto

volumes:
  postgres_data:
```

## Performance & Scalability

### System Capacity
- **Target Scale**: 10,000+ concurrent Raspberry Pi devices
- **API Efficiency**: Single NEA API subscription serves all customers
- **Geographic Optimization**: PostGIS spatial indexing for sub-second queries
- **Alert Latency**: <10 seconds from strike detection to LED activation
- **Hardware Reliability**: Autonomous operation with automatic alert clearing
- **Network Resilience**: MQTT with QoS 1 for guaranteed alert delivery

### Monitoring & Analytics
- **Real-time Dashboards**: System health, alert patterns, device status
- **Customer Analytics**: Strike frequency by location, alert effectiveness
- **Performance Metrics**: API response times, alert delivery success rates
- **Business Intelligence**: Subscription patterns, geographic coverage

## Business Benefits

### Cost Efficiency
- **Shared Infrastructure**: Single server serves thousands of customers
- **Reduced API Costs**: One API subscription vs. per-device costs
- **Operational Automation**: Minimal manual intervention required

### Competitive Advantages
- **Professional Reliability**: Redundant cloud infrastructure
- **Rapid Deployment**: Pre-configured Raspberry Pi devices with instant activation
- **Continuous Improvement**: Over-the-air updates and new features
- **Enterprise Ready**: Multi-location support and API integrations
- **Cost-Effective Hardware**: Raspberry Pi platform reduces device costs by 70%
- **Easy Installation**: Simple GPIO wiring and plug-and-play setup

## API Output Template

The NEA Lightning Alert API returns real-time lightning detection data in the following format:

```json
{
    "code": 0,
    "data": {
        "records": [
            {
                "datetime": "2025-09-02T11:36:00+08:00",
                "item": {
                    "isStationData": false,
                    "readings": [
                        {
                            "location": {
                                "latitude": "0.9817",
                                "longitude": "104.4199"
                            },
                            "type": "C",
                            "text": "Cloud to Cloud",
                            "datetime": "2025-09-02T11:35:37.681+08:00"
                        },
                        {
                            "location": {
                                "latitude": "1.0096",
                                "longitude": "104.3650"
                            },
                            "type": "C",
                            "text": "Cloud to Cloud",
                            "datetime": "2025-09-02T11:35:37.682+08:00"
                        },
                        {
                            "location": {
                                "latitude": "0.9631",
                                "longitude": "104.4316"
                            },
                            "type": "C",
                            "text": "Cloud to Cloud",
                            "datetime": "2025-09-02T11:35:37.682+08:00"
                        }
                    ],
                    "type": "observation"
                },
                "updatedTimestamp": "2025-09-02T11:38:02+08:00"
            }
        ]
    },
    "errorMsg": ""
}
```

### API Response Fields

- **code**: Response status code (0 for success)
- **data.records**: Array of lightning detection records
  - **datetime**: Record timestamp in ISO 8601 format with Singapore timezone (+08:00)
  - **item.isStationData**: Boolean indicating if data is from weather station
  - **item.readings**: Array of individual lightning strike readings
    - **location**: GPS coordinates of lightning strike
      - **latitude**: Latitude coordinate (decimal degrees)
      - **longitude**: Longitude coordinate (decimal degrees)
    - **type**: Lightning type code ("C" for Cloud to Cloud)
    - **text**: Human-readable lightning type description
    - **datetime**: Precise timestamp of lightning strike
  - **item.type**: Data type ("observation")
  - **updatedTimestamp**: Last update time of the record
- **errorMsg**: Error message (empty string when successful)

## Raspberry Pi Prototype Development

### Hardware Components

**Required Components:**
- **Raspberry Pi 4 Model B** (4GB RAM) - $75
- **MicroSD Card** 32GB Class 10 - $12
- **5mm LED** (Red/Yellow for visibility) - $0.50
- **220Ω Resistor** (current limiting) - $0.10
- **Jumper Wires** (Male-to-Female) - $2
- **Breadboard** (for prototyping) - $3
- **Weatherproof Enclosure** IP65 rated - $25
- **GPIO Header Extension** (optional) - $5

**Total Hardware Cost per Unit: ~$120**

### LED Alert Configuration

**GPIO Pin Assignment:**
- **GPIO 18** (Physical Pin 12) - LED Control Output
- **Ground** (Physical Pin 6) - LED Return Path
- **Alternative Pins**: GPIO 2, 3, 4, 17, 27, 22 for multiple LEDs

**Wiring Diagram:**
```
Raspberry Pi 4 GPIO Layout:
┌─────────────────────────────────┐
│  3V3  (1) ◯ ◯ (2)  5V          │
│  GPIO2 (3) ◯ ◯ (4)  5V          │
│  GPIO3 (5) ◯ ◯ (6)  GND  ───┐   │
│  GPIO4 (7) ◯ ◯ (8)  GPIO14     │   │
│  GND   (9) ◯ ◯ (10) GPIO15     │   │
│ GPIO17(11) ◯ ◯ (12) GPIO18 ──┐ │   │
│ GPIO27(13) ◯ ◯ (14) GND       │ │   │
│ GPIO22(15) ◯ ◯ (16) GPIO23    │ │   │
│  3V3  (17) ◯ ◯ (18) GPIO24    │ │   │
│ GPIO10(19) ◯ ◯ (20) GND       │ │   │
└─────────────────────────────────┘ │   │
                                    │   │
                   GPIO18 ──────────┘   │
                       │                │
                   220Ω Resistor        │
                       │                │
                   LED Anode (+)        │
                       │                │
                   LED Cathode (-) ─────┘
                   (Connected to Ground)
```

### Software Development Framework

**Development Environment Setup:**
```bash
# Install development dependencies
sudo apt update
sudo apt install -y python3.13-dev python3-venv git

# Clone repository
git clone https://github.com/Caisho/ura-lightning-detection.git
cd ura-lightning-detection

# Setup virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install Raspberry Pi specific dependencies
pip install -r requirements-raspberry-pi.txt
```

**requirements-raspberry-pi.txt:**
```
# Core dependencies
asyncio-mqtt>=0.16.1
paho-mqtt>=1.6.1
aiohttp>=3.9.0

# Raspberry Pi GPIO libraries
RPi.GPIO>=0.7.1
gpiozero>=1.6.2

# Development and testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
mock>=4.0.3

# Optional: GPIO simulation for development
fake-rpi>=0.7.1
```

### Development Workflow

**1. Local Development (Non-Raspberry Pi):**
```bash
# Use GPIO simulation for development on PC/Mac
export GPIOZERO_PIN_FACTORY=mock
python hardware/lightning_client.py test_device localhost

# Run unit tests with GPIO mocking
pytest tests/hardware/ -v
```

**2. Raspberry Pi Testing:**
```bash
# Deploy to Raspberry Pi
scp -r hardware/ pi@raspberrypi.local:/home/pi/lightning-alert/

# SSH into Raspberry Pi
ssh pi@raspberrypi.local

# Run client directly
cd lightning-alert
python hardware/lightning_client.py pi_garden_001 your-mqtt-broker.com

# Install as system service
sudo systemctl enable lightning-alert.service
sudo systemctl start lightning-alert.service
```

**3. Hardware Testing Commands:**
```bash
# Test LED manually
python -c "from gpiozero import LED; led = LED(18); led.blink()"

# Test MQTT connection
mosquitto_sub -h your-mqtt-broker.com -t "lightning/alerts/+"

# Send test alert
mosquitto_pub -h your-mqtt-broker.com -t "lightning/alerts/test_device" \
  -m '{"command":"TEST_ALERT","timestamp":"2025-09-02T11:35:37+08:00"}'
```

### Production Deployment

**Raspberry Pi Image Preparation:**
```bash
#!/bin/bash
# prepare_production_image.sh

# Base Raspberry Pi OS Lite setup
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.13 python3-pip git mosquitto-clients

# Create application user
sudo useradd -m -s /bin/bash lightning
sudo usermod -a -G gpio,spi,i2c lightning

# Install application
sudo -u lightning git clone https://github.com/Caisho/ura-lightning-detection.git /home/lightning/app
cd /home/lightning/app
sudo -u lightning python3.13 -m venv venv
sudo -u lightning ./venv/bin/pip install -r requirements-raspberry-pi.txt

# Configure systemd service
sudo cp config/lightning-alert.service /etc/systemd/system/
sudo systemctl enable lightning-alert.service

# Network configuration
sudo cp config/wpa_supplicant.conf.template /etc/wpa_supplicant/
sudo cp config/dhcpcd.conf.template /etc/

echo "Production image prepared. Configure WiFi and device ID before shipping."
```

### Customer Setup Process

**1. WiFi Configuration:**
```bash
# Customer configures WiFi via web interface at http://raspberrypi.local
# Or via mobile app with QR code setup

# Alternative: Pre-configuration file
cat > /boot/wpa_supplicant.conf << EOF
country=SG
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="CustomerWiFiNetwork"
    psk="CustomerPassword"
}
EOF
```

**2. Device Registration:**
```bash
# Automatic registration on first boot
curl -X POST https://api.yourdomain.com/v1/hardware/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "pi_'$(cat /proc/cpuinfo | grep Serial | cut -d: -f2)'",
    "device_type": "raspberry_pi_4",
    "activation_code": "'$ACTIVATION_CODE'",
    "location": {
      "latitude": '$GPS_LAT',
      "longitude": '$GPS_LON'
    }
  }'
```

### Monitoring and Maintenance

**Remote Monitoring Dashboard:**
- Device online/offline status
- Last heartbeat timestamp
- Alert response times
- LED functionality status
- Network connectivity health

**Over-the-Air Updates:**
```python
# update_manager.py - Remote update capability
import subprocess
import logging
from pathlib import Path

async def check_for_updates():
    """Check for software updates from server"""
    current_version = get_current_version()
    latest_version = await fetch_latest_version()
    
    if latest_version > current_version:
        await download_and_apply_update(latest_version)
        restart_service()

def get_current_version():
    return Path("/home/lightning/app/VERSION").read_text().strip()

async def download_and_apply_update(version):
    """Download and apply software update"""
    subprocess.run([
        "git", "fetch", "origin", f"v{version}"
    ], cwd="/home/lightning/app")
    
    subprocess.run([
        "git", "checkout", f"v{version}"
    ], cwd="/home/lightning/app")
    
    subprocess.run([
        "./venv/bin/pip", "install", "-r", "requirements-raspberry-pi.txt"
    ], cwd="/home/lightning/app")

def restart_service():
    """Restart the lightning alert service"""
    subprocess.run(["sudo", "systemctl", "restart", "lightning-alert.service"])
```

## Hardware Lightning Alert System Guidelines

### System Architecture

### Centralized Server with Location-Based Alert Targeting
- **Central Monitoring Server**: Single server polls NEA Lightning Alert API
- **Customer Database**: Tracks all subscribers, their hardware, and precise locations
- **Intelligent Alert Distribution**: Server calculates distance and sends alerts only to affected customers
- **Hardware Registry**: Each device linked to customer account and GPS coordinates
- **Geographic Processing**: Real-time proximity calculations for targeted alerts

### Benefits of Location-Targeted Architecture
- **Bandwidth Efficient**: Only sends alerts to hardware within strike radius
- **Reduced False Alerts**: Customers only receive relevant location-based warnings
- **Network Optimization**: Minimizes unnecessary data transmission
- **Battery Conservation**: Hardware units sleep when not in alert zones
- **Scalable Performance**: System efficiency improves with geographic distribution

## Location-Based Alert Processing

### Customer Database Schema

Each customer record contains:
```json
{
  "customer_id": "cust_12345",
  "email": "customer@example.com",
  "first_name": "John",
  "last_name": "Tan",
  "phone": "+65-9123-4567",
  "subscription_tier": "premium",
  "subscription_status": "active",
  "joined_at": "2024-09-02T14:30:00+08:00",
  
  "current_subscription": {
    "subscription_id": "sub_67890",
    "subscription_type": "annual",
    "started_at": "2024-09-02T14:30:00+08:00",
    "expires_at": "2025-09-02T14:30:00+08:00",
    "status": "active",
    "billing_amount": 299.00,
    "billing_currency": "SGD"
  },
  
  "hardware_units": [
    {
      "device_id": "hw_67890",
      "device_type": "led_signage",
      "device_name": "Home - Garden Alert",
      "location": {
        "latitude": 1.3521,
        "longitude": 103.8198
      },
      "address": {
        "address_line_1": "123 Orchard Road",
        "address_line_2": "#12-34",
        "postal_code": "238874",
        "building_name": "Orchard Tower",
        "unit_number": "12-34"
      },
      "alert_radius_km": 8,
      "status": "active",
      "last_seen": "2025-09-02T11:30:00+08:00",
      "firmware_version": "1.2.3",
      "installation_date": "2024-09-05"
    }
  ],
  
  "notification_preferences": {
    "email": "customer@example.com",
    "sms": "+65-9123-4567",
    "push_notifications": true
  }
}
```

## Database Design Principles & Security

### 1. Separation of Concerns

**Customer Table**: Core customer information only
- Personal details (name, email, phone)
- Account status (active/inactive/suspended)
- Account lifecycle (joined_at)

**Subscriptions Table**: Subscription lifecycle tracking
- Multiple subscriptions per customer (renewals, upgrades)
- Complete audit trail of subscription changes
- Billing amounts (non-sensitive pricing data)

**Payments Table**: Payment processing tracking
- Links to external payment gateways
- No sensitive card/bank details stored
- Payment status and reference tracking

### 2. Security Best Practices

**What We DON'T Store:**
- Credit card numbers, CVV, expiry dates
- Bank account details
- Payment gateway tokens (store in secure vault)
- Personal identification numbers

**What We DO Store:**
- Payment gateway transaction references
- Payment amounts and currency
- Payment method types (generic)
- Payment status for reconciliation

**External Payment Integration:**
```python
# Example: Secure payment processing
async def process_payment(customer_id: str, amount: Decimal):
    # Use external payment gateway (Stripe, PayPal, etc.)
    payment_intent = await stripe.create_payment_intent(
        amount=amount,
        currency='SGD',
        customer=customer_id
    )
    
    # Store only reference, not sensitive data
    payment_record = {
        'subscription_id': subscription_id,
        'payment_reference': payment_intent.id,
        'amount': amount,
        'payment_status': 'pending'
    }
    
    return await create_payment_record(payment_record)
```

### 3. Singapore Address Validation

**Postal Code Integration:**
```python
# Singapore postal code validation and address lookup
async def validate_singapore_address(postal_code: str):
    # Use Singapore OneMap API for address validation
    async with aiohttp.ClientSession() as session:
        url = f"https://developers.onemap.sg/commonapi/search?searchVal={postal_code}&returnGeom=Y"
        async with session.get(url) as response:
            data = await response.json()
            
            if data['found'] > 0:
                result = data['results'][0]
                return {
                    'address': result['ADDRESS'],
                    'building': result['BUILDING'],
                    'latitude': float(result['LATITUDE']),
                    'longitude': float(result['LONGITUDE']),
                    'postal_code': result['POSTAL']
                }
    
    raise ValueError("Invalid Singapore postal code")
```

### 4. Customer-Hardware Relationship Benefits

**One-to-Many Design Advantages:**
- **Multi-location customers**: Homes, offices, warehouses
- **Device management**: Different alert radius per location
- **Service efficiency**: Technician dispatch by postal code
- **Billing flexibility**: Per-device pricing models
- **Compliance**: Singapore address for regulatory requirements

**Hardware Lifecycle Tracking:**
- **Installation tracking**: When device was deployed
- **Maintenance scheduling**: Based on installation date
- **Firmware management**: Version tracking and updates
- **Service history**: Maintenance and support records

### 5. Query Examples for New Schema

```python
# Get customer with active subscription and hardware
async def get_customer_details(customer_id: str):
    query = text("""
        SELECT 
            c.*,
            s.subscription_type, s.started_at, s.expires_at, s.status as sub_status,
            h.device_id, h.device_name, h.address_line_1, h.postal_code,
            ST_X(h.location::geometry) as longitude,
            ST_Y(h.location::geometry) as latitude
        FROM customers c
        LEFT JOIN subscriptions s ON c.id = s.customer_id 
            AND s.status = 'active'
        LEFT JOIN hardware_units h ON c.id = h.customer_id 
            AND h.status = 'active'
        WHERE c.id = :customer_id
    """)
    
    return await database.fetch_all(query, values={"customer_id": customer_id})

# Get devices by postal code for technician dispatch
async def get_devices_by_area(postal_code_prefix: str):
    query = text("""
        SELECT 
            h.device_id, h.device_name, h.address_line_1, h.postal_code,
            c.email, c.phone, h.status, h.last_seen
        FROM hardware_units h
        JOIN customers c ON h.customer_id = c.id
        WHERE h.postal_code LIKE :postal_prefix
        ORDER BY h.postal_code, h.address_line_1
    """)
    
    return await database.fetch_all(
        query, 
        values={"postal_prefix": f"{postal_code_prefix}%"}
    )

# Subscription renewal tracking
async def get_expiring_subscriptions(days_ahead: int = 30):
    query = text("""
        SELECT 
            c.email, c.first_name, c.last_name,
            s.subscription_type, s.expires_at, s.billing_amount,
            COUNT(h.id) as device_count
        FROM customers c
        JOIN subscriptions s ON c.id = s.customer_id
        LEFT JOIN hardware_units h ON c.id = h.customer_id AND h.status = 'active'
        WHERE s.status = 'active'
        AND s.expires_at <= NOW() + INTERVAL ':days days'
        AND s.expires_at > NOW()
        GROUP BY c.id, s.id
        ORDER BY s.expires_at ASC
    """)
    
    return await database.fetch_all(query, values={"days": days_ahead})
```
}
```

### Intelligent Alert Distribution Algorithm

**Step 1: Lightning Strike Processing**
```python
# Pseudo-code for alert distribution
def process_lightning_strike(strike_data):
    strike_lat = strike_data.latitude
    strike_lon = strike_data.longitude
    strike_time = strike_data.datetime
    
    affected_customers = []
    
    # Query all active customers and their hardware
    for customer in get_active_customers():
        for hardware in customer.hardware_units:
            distance = calculate_distance(
                strike_lat, strike_lon,
                hardware.location.latitude, 
                hardware.location.longitude
            )
            
            if distance <= hardware.alert_radius_km:
                affected_customers.append({
                    'customer': customer,
                    'hardware': hardware,
                    'distance': distance,
                    'strike_time': strike_time
                })
    
    # Send targeted alerts only to affected customers
    send_targeted_alerts(affected_customers, strike_data)
```

**Step 2: Targeted Alert Delivery**
- Server sends alerts **only** to hardware units within strike radius
- Each alert includes customer-specific information and strike distance
- Hardware units outside radius remain in standby mode
- Hardware manages its own 30-minute countdown timer for auto-clearing
- Reduces network traffic by 80-95% compared to broadcast alerts

### Alert Flow Process

1. **API Monitoring**: Server polls NEA Lightning Alert API every 30 seconds
2. **Strike Detection**: Server receives new lightning strike coordinates
3. **Database Query**: Server retrieves all active customer locations from database
4. **Distance Calculation**: Server calculates distance from strike to each hardware unit
5. **Proximity Filtering**: Only hardware within configured radius (5km/8km/custom) selected
6. **Personalized Alerts**: Server sends individualized alerts with customer-specific data
7. **Hardware Activation**: Only relevant units receive commands and activate alerts
8. **Auto-Clearing Logic**: Hardware automatically clears alerts after 30 minutes without new messages
9. **Timer Reset**: New alert messages reset the hardware's 30-minute countdown timer

### Geographic Optimization Features

**Spatial Indexing**:
- Use PostGIS or MongoDB with geospatial indexing
- Enable rapid proximity queries for thousands of customers
- Support complex geographic shapes (not just radius circles)

**Regional Processing**:
- Divide Singapore into grid sectors for processing efficiency
- Pre-filter customers by geographic region before distance calculations
- Scale to handle multiple simultaneous lightning strikes

**Real-time Performance**:
- Target: Alert delivery within 10 seconds of API detection
- Batch process multiple strikes efficiently
- Queue system for handling peak storm loads

- **Real-time performance** targets (10-second alert delivery)

## Hardware Auto-Clearing Mechanism

### Server-to-Hardware Communication Protocol

**Alert Activation Message**:
```json
{
  "command": "LIGHTNING_ALERT",
  "alert_id": "alert_20250902_113537",
  "timestamp": "2025-09-02T11:35:37+08:00",
  "subscriber_id": "sub_12345",
  "lightning_data": {
    "distance_km": 6.2,
    "strike_time": "2025-09-02T11:35:37+08:00",
    "strike_location": {
      "latitude": 1.3087,
      "longitude": 103.8542
    }
  },
  "alert_level": "HIGH"
}
```

### Hardware Timer Management

**Auto-Clearing Logic**:
- Hardware starts **30-minute countdown timer** upon receiving first alert message
- Timer continues running while visual alerts are active
- **Timer resets to 30 minutes** each time a new alert message is received
- **Automatic clear** when timer reaches zero with no new messages
- No server communication required for clearing alerts

**Hardware State Management**:
```python
# Pseudo-code for hardware timer logic
class LightningAlertHardware:
    def __init__(self):
        self.alert_active = False
        self.clear_timer = None
        self.alert_timeout = 30 * 60  # 30 minutes in seconds
    
    def on_alert_received(self, alert_message):
        # Reset/start the 30-minute timer
        if self.clear_timer:
            self.clear_timer.cancel()
        
        self.activate_visual_alerts()
        self.alert_active = True
        
        # Start new 30-minute countdown
        self.clear_timer = Timer(self.alert_timeout, self.auto_clear_alert)
        self.clear_timer.start()
    
    def auto_clear_alert(self):
        # Automatically clear after 30 minutes of no new alerts
        self.deactivate_visual_alerts()
        self.alert_active = False
        self.clear_timer = None
```

### Benefits of Hardware Auto-Clearing

**Network Efficiency**:
- **No clear messages** needed from server - reduces bandwidth by 50%
- **Simplified server logic** - no need to track individual customer alert states
- **Reduced latency** - no server-to-hardware round trip for clearing

**Reliability**:
- **Network resilient** - alerts clear even if connection lost
- **Server independent** - hardware operates autonomously for safety
- **Battery efficient** - fewer network communications

**Operational Advantages**:
- **Simplified debugging** - clear logic contained in hardware
- **Reduced server load** - no alert state management needed
- **Failsafe operation** - alerts automatically clear without server intervention

## Subscription Management Integration

### Hardware Registration Process

1. **Customer Account Creation**: Web portal registration with location verification
2. **Raspberry Pi Provisioning**: Device shipped pre-configured with unique ID and activation code
3. **Location Setup**: Customer provides precise GPS coordinates via mobile app or web portal
4. **Network Configuration**: Raspberry Pi connects to customer WiFi using setup wizard
5. **LED Installation**: Simple GPIO wiring to external LED for visual alerts
6. **Service Activation**: Server adds hardware to customer database and begins monitoring

### Multi-Location Support

**Premium/Commercial Features**:
- Multiple Raspberry Pi units per customer account
- Different alert radius per location (home: 8km, office: 5km, warehouse: 12km)
- Location-specific notification preferences
- Centralized management dashboard for all devices

### Customer Portal Features

**Location Management**:
- Interactive map for setting precise hardware coordinates
- Test alert functionality to verify hardware response
- Alert history per location with strike distances
- Performance analytics and uptime monitoring

## Lightning Observation API Documentation

### Endpoint
`GET https://api-open.data.gov.sg/v2/real-time/api/weather?api=lightning`

### Description
Retrieve the latest lightning observation in Singapore. Data is updated multiple times throughout the day.

### Query Parameters
| Name            | Type   | Required | Description                                                                 |
|-----------------|--------|----------|-----------------------------------------------------------------------------|
| api             | string | Yes      | Set the value to `lightning` to fetch lightning records                     |
| date            | string | No       | SGT date in `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS` format.                   |
|                 |        |          | Example: `2025-01-16` or `2025-01-16T23:59:00`                              |
| paginationToken | string | No       | Token for retrieving subsequent data pages (only for requests with date)     |

If `date` is not provided, the API returns the latest lightning observation.

### Headers
| Name      | Type   | Required | Description                                         |
|-----------|--------|----------|-----------------------------------------------------|
| x-api-key | string | No       | API key for higher rate limits (optional)           |

### Example Requests

**Retrieve latest observation:**
```
GET https://api-open.data.gov.sg/v2/real-time/api/weather?api=lightning
```

**Retrieve all readings for a specific day:**
```
GET https://api-open.data.gov.sg/v2/real-time/api/weather?api=lightning&date=2025-01-16
```

**Retrieve readings for a specific date-time:**
```
GET https://api-open.data.gov.sg/v2/real-time/api/weather?api=lightning&date=2025-01-16T23:59:00
```

### Responses

#### 200 OK
Returns lightning observations in JSON format.

#### 400 Bad Request
Invalid HTTP request body.

#### 404 Not Found
Weather data not found.

## Usage

[Add usage instructions here]