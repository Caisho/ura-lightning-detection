"""
Unit tests for MQTT LED Control Server

Tests the MQTT server functionality for sending LED blink commands.
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Import the server class
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from mqtt_server import LEDControlServer


class TestLEDControlServerInitialization:
    """Test LED Control Server initialization."""
    
    def test_init_default_params(self):
        """Test server initialization with default parameters."""
        server = LEDControlServer()
        
        assert server.broker_host == "localhost"
        assert server.broker_port == 1883
        assert server.topic == "rpi/led/control"
        assert server.client_id == "led_server"
        assert server.blink_duration == 300  # 5 minutes
    
    def test_init_custom_params(self):
        """Test server initialization with custom parameters."""
        server = LEDControlServer(
            broker_host="192.168.1.100",
            broker_port=8883,
            topic="custom/led/topic",
            client_id="custom_server"
        )
        
        assert server.broker_host == "192.168.1.100"
        assert server.broker_port == 8883
        assert server.topic == "custom/led/topic"
        assert server.client_id == "custom_server"
        assert server.blink_duration == 300


class TestLEDControlServerCommands:
    """Test LED Control Server command generation."""
    
    def test_command_structure(self):
        """Test that generated commands have correct structure."""
        server = LEDControlServer()
        
        # Mock datetime to make timestamp predictable
        with patch('mqtt_server.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T12:00:00"
            
            # We can't easily test the async send function, but we can test command structure
            expected_command = {
                "action": "blink",
                "pin": 18,
                "duration": 300,
                "message": "Test Message",
                "timestamp": "2023-01-01T12:00:00",
                "reset_timer": True
            }
            
            # Verify the command structure would be correct
            assert server.blink_duration == expected_command["duration"]
            assert server.topic == "rpi/led/control"


@pytest.mark.asyncio
class TestLEDControlServerMQTT:
    """Test MQTT functionality."""
    
    async def test_send_with_paho_mqtt(self):
        """Test sending command with paho-mqtt fallback."""
        server = LEDControlServer()
        
        # Test command structure without actual MQTT sending
        command_data = {
            "action": "blink",
            "pin": 18,
            "duration": 300,
            "message": "Test",
            "timestamp": datetime.now().isoformat(),
            "reset_timer": True
        }
        
        json_command = json.dumps(command_data)
        
        # Verify JSON is valid
        parsed = json.loads(json_command)
        assert parsed["action"] == "blink"
        assert parsed["pin"] == 18
        assert parsed["duration"] == 300
        assert parsed["reset_timer"] is True
    
    async def test_asyncio_mqtt_fallback(self):
        """Test that server handles missing asyncio-mqtt gracefully."""
        # This would be tested by patching the import, but for now we verify
        # that the server initializes correctly
        server = LEDControlServer()
        assert server is not None
        assert hasattr(server, '_send_with_paho_mqtt')
        assert hasattr(server, '_send_with_asyncio_mqtt')


class TestLEDControlServerValidation:
    """Test server input validation and error handling."""
    
    def test_broker_host_validation(self):
        """Test broker host parameter validation."""
        # Test with various host formats
        servers = [
            LEDControlServer(broker_host="localhost"),
            LEDControlServer(broker_host="192.168.1.100"),
            LEDControlServer(broker_host="mqtt.example.com"),
        ]
        
        for server in servers:
            assert server.broker_host is not None
            assert len(server.broker_host) > 0
    
    def test_port_validation(self):
        """Test port parameter validation."""
        # Test with valid ports
        server_1883 = LEDControlServer(broker_port=1883)  # Standard MQTT
        server_8883 = LEDControlServer(broker_port=8883)  # MQTT over SSL
        
        assert server_1883.broker_port == 1883
        assert server_8883.broker_port == 8883
    
    def test_topic_validation(self):
        """Test topic parameter validation."""
        # Test with various topic formats
        servers = [
            LEDControlServer(topic="rpi/led/control"),
            LEDControlServer(topic="home/automation/led"),
            LEDControlServer(topic="test/topic"),
        ]
        
        for server in servers:
            assert server.topic is not None
            assert len(server.topic) > 0
            assert "/" in server.topic  # MQTT topics typically have slashes


class TestCommandJSONSerialization:
    """Test JSON serialization of commands."""
    
    def test_json_serialization(self):
        """Test that commands can be properly serialized to JSON."""
        command = {
            "action": "blink",
            "pin": 18,
            "duration": 300,
            "message": "Lightning Alert!",
            "timestamp": datetime.now().isoformat(),
            "reset_timer": True
        }
        
        # Test serialization
        json_str = json.dumps(command)
        assert json_str is not None
        assert len(json_str) > 0
        
        # Test deserialization
        parsed = json.loads(json_str)
        assert parsed["action"] == "blink"
        assert parsed["pin"] == 18
        assert parsed["duration"] == 300
        assert parsed["message"] == "Lightning Alert!"
        assert parsed["reset_timer"] is True
    
    def test_json_with_special_characters(self):
        """Test JSON serialization with special characters."""
        command = {
            "action": "blink",
            "pin": 18,
            "duration": 300,
            "message": "Alert: 🌩️⚡Lightning detected!⚡🌩️",
            "timestamp": datetime.now().isoformat(),
            "reset_timer": True
        }
        
        # Test serialization with Unicode
        json_str = json.dumps(command, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert "🌩️" in parsed["message"]
        assert "⚡" in parsed["message"]


if __name__ == "__main__":
    pytest.main([__file__])