# GPIO LED Client-Server System

This system provides MQTT-based client-server communication for controlling GPIO LEDs on Raspberry Pi devices. When the server script is run, it sends a command to the client Raspberry Pi to blink GPIO LED (pin 18) for 5 minutes. If the script is run again within that 5 minutes, the timer resets to 5 minutes again.

## Architecture

- **MQTT Server** (`src/mqtt_server.py`): Sends LED blink commands via MQTT
- **MQTT Client** (`src/mqtt_client.py`): Receives commands and controls GPIO LED on Raspberry Pi
- **MQTT Broker**: Eclipse Mosquitto broker for reliable message delivery
- **Docker Support**: Complete containerization for easy deployment

## Quick Start

### 1. Install Dependencies

For Raspberry Pi (client):
```bash
pip install -r requirements-rpi.txt
```

For server (any Linux system):
```bash
pip install paho-mqtt asyncio-mqtt
```

### 2. Start MQTT Broker

Using Docker:
```bash
docker-compose -f docker-compose-client.yml up -d mqtt-broker
```

Or install Mosquitto locally:
```bash
sudo apt-get install mosquitto mosquitto-clients
sudo systemctl start mosquitto
```

### 3. Start LED Client (on Raspberry Pi)

Direct execution:
```bash
python src/mqtt_client.py --broker <broker-ip>
```

Or using Docker:
```bash
docker-compose -f docker-compose-client.yml up -d led-client
```

### 4. Send LED Commands (from server)

```bash
python src/mqtt_server.py --broker <broker-ip> --message "Lightning Alert!"
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_BROKER` | localhost | MQTT broker hostname |
| `MQTT_PORT` | 1883 | MQTT broker port |
| `MQTT_TOPIC` | rpi/led/control | MQTT topic for commands |
| `LED_PIN` | 18 | GPIO pin number for LED |

### Command Structure

The MQTT commands use JSON format:

```json
{
    "action": "blink",
    "pin": 18,
    "duration": 300,
    "message": "Lightning Alert!",
    "timestamp": "2023-01-01T12:00:00",
    "reset_timer": true
}
```

## Docker Deployment

### Complete Stack

Start all services (MQTT broker + LED client):
```bash
docker-compose -f docker-compose-client.yml up -d
```

### Development with Server

Start with optional server container for testing:
```bash
docker-compose -f docker-compose-client.yml --profile server up -d
```

Send command from server container:
```bash
docker-compose -f docker-compose-client.yml exec led-server \
  python src/mqtt_server.py --broker mqtt-broker
```

### View Logs

```bash
# Client logs
docker-compose -f docker-compose-client.yml logs -f led-client

# Broker logs  
docker-compose -f docker-compose-client.yml logs -f mqtt-broker
```

## Hardware Setup

### LED Connection

Connect LED to Raspberry Pi GPIO:
- **Anode (+)**: GPIO 18 (Pin 12)
- **Cathode (-)**: Ground (Pin 6) through 330Ω resistor

### GPIO Libraries

The client supports multiple GPIO libraries:
1. **gpiozero** (recommended): Modern, simple interface
2. **RPi.GPIO**: Traditional GPIO library
3. **Mock GPIO**: For testing on non-Pi systems

## Features

### ✅ Implemented Features

- **5-minute LED blink duration**: Configurable via command
- **Timer reset functionality**: New commands reset the 5-minute timer
- **MQTT communication**: Reliable, async message delivery
- **Docker containerization**: Easy deployment and scaling
- **Mock GPIO support**: Testing on non-Raspberry Pi systems
- **Comprehensive logging**: Debug and monitor system activity
- **Graceful shutdown**: Proper cleanup of GPIO resources
- **Multiple GPIO libraries**: Fallback support for different setups

### 🔧 Technical Features

- **Async/await support**: Non-blocking LED control
- **Signal handling**: Graceful shutdown on SIGINT/SIGTERM
- **Health checks**: Docker health monitoring
- **Error handling**: Robust error recovery
- **JSON validation**: Secure command processing
- **Configurable parameters**: Flexible deployment options

## Usage Examples

### Basic LED Control

```bash
# Start client (on Raspberry Pi)
python src/mqtt_client.py

# Send blink command (from any system)
python src/mqtt_server.py --message "Alert: Lightning detected!"
```

### Custom Configuration

```bash
# Custom MQTT broker and topic
python src/mqtt_client.py --broker 192.168.1.100 --topic "home/alerts/led"
python src/mqtt_server.py --broker 192.168.1.100 --topic "home/alerts/led"
```

### Docker with Custom Network

```bash
# Create custom network
docker network create lightning-network

# Start with custom config
MQTT_BROKER=custom-broker docker-compose -f docker-compose-client.yml up -d
```

## Testing

### Unit Tests

Run all tests:
```bash
pytest tests/
```

Run MQTT-specific tests:
```bash
pytest tests/unit/test_mqtt_server.py tests/unit/test_mqtt_client.py -v
```

### Integration Testing

Test with real MQTT broker:
```bash
# Terminal 1: Start broker
docker run -it -p 1883:1883 eclipse-mosquitto:2.0

# Terminal 2: Start client
python src/mqtt_client.py

# Terminal 3: Send command
python src/mqtt_server.py --message "Test Alert"
```

## Troubleshooting

### Common Issues

1. **GPIO Permission Denied**
   ```bash
   sudo usermod -a -G gpio $USER
   # Logout and login again
   ```

2. **MQTT Connection Failed**
   ```bash
   # Check broker is running
   docker-compose -f docker-compose-client.yml logs mqtt-broker
   
   # Test connectivity
   mosquitto_pub -h localhost -t test -m "hello"
   ```

3. **Docker GPIO Access**
   ```bash
   # Ensure privileged mode and device mounts
   privileged: true
   volumes:
     - /dev/gpiomem:/dev/gpiomem
   ```

### Debugging

Enable debug logging:
```bash
export PYTHONPATH=/path/to/project
python -c "import logging; logging.basicConfig(level=logging.DEBUG)"
python src/mqtt_client.py
```

View Docker logs:
```bash
docker-compose -f docker-compose-client.yml logs -f --tail=100
```

## Security Considerations

### Production Deployment

1. **Enable MQTT Authentication**:
   - Configure username/password in mosquitto.conf
   - Use TLS/SSL encryption (port 8883)

2. **Network Security**:
   - Use private MQTT broker
   - Configure firewall rules
   - Use VPN for remote access

3. **Docker Security**:
   - Use non-root user in containers
   - Limit privileged access
   - Regular security updates

### Example Secure Configuration

```yaml
# docker-compose-client.yml
services:
  mqtt-broker:
    environment:
      - MOSQUITTO_USERNAME=lightninguser
      - MOSQUITTO_PASSWORD=securepassword
    ports:
      - "8883:8883"  # TLS port only
```

## Integration with Lightning Detection

This GPIO LED system can be integrated with the main lightning detection system:

```python
# In your lightning detection code
from src.mqtt_server import LEDControlServer

async def on_lightning_detected():
    server = LEDControlServer(broker_host="raspberry-pi-ip")
    await server.send_blink_command("⚡ Lightning Alert! ⚡")
```

## Contributing

1. Follow existing code style (ruff formatter)
2. Add tests for new features
3. Update documentation
4. Test on actual Raspberry Pi hardware when possible

## License

Same as main project license.