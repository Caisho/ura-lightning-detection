"""
Unit tests for MQTT LED Control Client

Tests the MQTT client functionality for receiving LED blink commands.
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

# Import the client classes
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from mqtt_client import LEDControlClient, GPIOLEDController, MockLED


class TestMockLED:
    """Test Mock LED functionality for non-Raspberry Pi environments."""
    
    def test_mock_led_initialization(self):
        """Test MockLED initialization."""
        led = MockLED(pin=18)
        
        assert led.pin == 18
        assert led.is_lit is False
    
    def test_mock_led_on_off(self):
        """Test MockLED on/off functionality."""
        led = MockLED(pin=18)
        
        # Test turning on
        led.on()
        assert led.is_lit is True
        
        # Test turning off
        led.off()
        assert led.is_lit is False
    
    def test_mock_led_blink(self):
        """Test MockLED blink method."""
        led = MockLED(pin=18)
        
        # Should not raise any exceptions
        led.blink(on_time=0.5, off_time=0.5, n=3, background=True)
        led.close()


class TestGPIOLEDController:
    """Test GPIO LED Controller functionality."""
    
    def test_controller_initialization(self):
        """Test GPIO LED Controller initialization."""
        with patch('mqtt_client.GPIO_AVAILABLE', False):
            controller = GPIOLEDController(pin=18)
            
            assert controller.pin == 18
            assert controller.blink_task is None
            assert controller.current_end_time is None
            assert controller.is_running is False
            assert isinstance(controller.led, MockLED)
    
    @pytest.mark.asyncio
    async def test_turn_on_off(self):
        """Test LED on/off functionality."""
        with patch('mqtt_client.GPIO_AVAILABLE', False):
            controller = GPIOLEDController(pin=18)
            
            # Test turning on
            await controller._turn_on()
            assert controller.led.is_lit is True
            
            # Test turning off
            await controller._turn_off()
            assert controller.led.is_lit is False
    
    @pytest.mark.asyncio
    async def test_start_blink(self):
        """Test starting LED blink functionality."""
        with patch('mqtt_client.GPIO_AVAILABLE', False):
            controller = GPIOLEDController(pin=18)
            
            # Start a short blink (1 second for testing)
            await controller.start_blink(duration=1, reset_timer=True)
            
            # Verify task was created
            assert controller.blink_task is not None
            assert controller.current_end_time is not None
            
            # Wait for completion
            await asyncio.sleep(1.5)
            
            # Clean up
            controller.cleanup()
    
    @pytest.mark.asyncio
    async def test_stop_blink(self):
        """Test stopping LED blink functionality."""
        with patch('mqtt_client.GPIO_AVAILABLE', False):
            controller = GPIOLEDController(pin=18)
            
            # Start blink
            await controller.start_blink(duration=10, reset_timer=True)
            
            # Stop immediately
            await controller.stop_blink()
            
            # Verify it stopped
            assert controller.is_running is False
            assert controller.led.is_lit is False
            
            controller.cleanup()
    
    @pytest.mark.asyncio
    async def test_timer_reset(self):
        """Test timer reset functionality."""
        with patch('mqtt_client.GPIO_AVAILABLE', False):
            controller = GPIOLEDController(pin=18)
            
            # Start first blink
            await controller.start_blink(duration=10, reset_timer=True)
            first_end_time = controller.current_end_time
            
            # Wait a bit
            await asyncio.sleep(0.1)
            
            # Start second blink (should reset timer)
            await controller.start_blink(duration=15, reset_timer=True)
            second_end_time = controller.current_end_time
            
            # Verify timer was reset (new end time should be later)
            assert second_end_time > first_end_time
            
            # Clean up
            await controller.stop_blink()
            controller.cleanup()


class TestLEDControlClient:
    """Test LED Control Client functionality."""
    
    def test_client_initialization(self):
        """Test LED Control Client initialization."""
        client = LEDControlClient(
            broker_host="test-broker",
            broker_port=1884,
            topic="test/topic",
            client_id="test_client"
        )
        
        assert client.broker_host == "test-broker"
        assert client.broker_port == 1884
        assert client.topic == "test/topic"
        assert client.client_id == "test_client"
        assert client.running is True
        assert client.led_controller is not None
    
    @pytest.mark.asyncio
    async def test_process_command_blink(self):
        """Test processing blink command."""
        with patch('mqtt_client.GPIO_AVAILABLE', False):
            client = LEDControlClient()
            
            command = {
                "action": "blink",
                "pin": 18,
                "duration": 1,  # Short duration for testing
                "message": "Test Alert",
                "reset_timer": True,
                "timestamp": datetime.now().isoformat()
            }
            
            # Process command
            await client.process_command(command)
            
            # Verify LED controller received the command
            assert client.led_controller.current_end_time is not None
            
            # Clean up
            await client.shutdown()
    
    @pytest.mark.asyncio
    async def test_process_unknown_command(self):
        """Test processing unknown command."""
        with patch('mqtt_client.GPIO_AVAILABLE', False):
            client = LEDControlClient()
            
            command = {
                "action": "unknown_action",
                "pin": 18,
                "duration": 5,
                "message": "Test",
                "timestamp": datetime.now().isoformat()
            }
            
            # Should not raise exception
            await client.process_command(command)
            
            await client.shutdown()
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test client shutdown functionality."""
        with patch('mqtt_client.GPIO_AVAILABLE', False):
            client = LEDControlClient()
            
            # Start a blink operation
            command = {
                "action": "blink",
                "pin": 18,
                "duration": 10,
                "message": "Test",
                "reset_timer": True
            }
            await client.process_command(command)
            
            # Shutdown
            await client.shutdown()
            
            # Verify shutdown
            assert client.running is False
            assert client.led_controller.is_running is False


class TestCommandProcessing:
    """Test command processing and validation."""
    
    @pytest.mark.asyncio
    async def test_command_with_missing_fields(self):
        """Test command processing with missing fields."""
        with patch('mqtt_client.GPIO_AVAILABLE', False):
            client = LEDControlClient()
            
            # Command with minimal fields
            command = {
                "action": "blink"
                # Missing other fields - should use defaults
            }
            
            await client.process_command(command)
            
            # Should have used default values
            assert client.led_controller.current_end_time is not None
            
            await client.shutdown()
    
    @pytest.mark.asyncio
    async def test_command_with_custom_pin(self):
        """Test command processing with custom pin."""
        with patch('mqtt_client.GPIO_AVAILABLE', False):
            client = LEDControlClient()
            
            command = {
                "action": "blink",
                "pin": 22,  # Different pin
                "duration": 1,
                "message": "Custom pin test"
            }
            
            # Should process without error
            await client.process_command(command)
            
            await client.shutdown()
    
    @pytest.mark.asyncio
    async def test_invalid_json_handling(self):
        """Test handling of invalid JSON data."""
        with patch('mqtt_client.GPIO_AVAILABLE', False):
            client = LEDControlClient()
            
            # This would typically be tested at the MQTT message level
            # but we can test the command processing directly
            invalid_command = {}  # Empty command
            
            # Should not raise exception
            await client.process_command(invalid_command)
            
            await client.shutdown()


class TestTimerFunctionality:
    """Test timer reset and duration functionality."""
    
    @pytest.mark.asyncio
    async def test_five_minute_duration(self):
        """Test default 5-minute duration."""
        with patch('mqtt_client.GPIO_AVAILABLE', False):
            controller = GPIOLEDController(pin=18)
            
            await controller.start_blink(duration=300, reset_timer=True)  # 5 minutes
            
            # Verify end time is approximately 5 minutes from now
            now = datetime.now()
            expected_end = now + timedelta(seconds=300)
            
            # Allow for small timing differences
            time_diff = abs((controller.current_end_time - expected_end).total_seconds())
            assert time_diff < 2  # Within 2 seconds
            
            await controller.stop_blink()
            controller.cleanup()
    
    @pytest.mark.asyncio
    async def test_timer_reset_scenario(self):
        """Test the specific scenario: reset timer if new command within 5 minutes."""
        with patch('mqtt_client.GPIO_AVAILABLE', False):
            controller = GPIOLEDController(pin=18)
            
            # Start first blink (simulate 5 minutes)
            await controller.start_blink(duration=300, reset_timer=True)
            first_end_time = controller.current_end_time
            
            # Wait a short time (simulate 1 minute passing)
            await asyncio.sleep(0.1)
            
            # Send second command (should reset timer)
            await controller.start_blink(duration=300, reset_timer=True)
            second_end_time = controller.current_end_time
            
            # Second end time should be later than first (timer reset)
            assert second_end_time > first_end_time
            
            # Clean up
            await controller.stop_blink()
            controller.cleanup()


if __name__ == "__main__":
    pytest.main([__file__])