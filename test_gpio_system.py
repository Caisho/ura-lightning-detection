#!/usr/bin/env python3
"""
Test script for GPIO LED Client-Server System

This script demonstrates the GPIO LED control system by running both
client and server components for testing purposes.
"""

import asyncio
import json
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_mock_gpio():
    """Test Mock GPIO functionality."""
    print("🔧 Testing Mock GPIO LED...")

    # Import the mock LED
    from src.mqtt_client import MockLED

    led = MockLED(pin=18)

    print(f"✅ LED created on pin {led.pin}")

    # Test basic operations
    led.on()
    time.sleep(0.5)
    led.off()
    time.sleep(0.5)

    led.blink(on_time=0.2, off_time=0.2, n=3)
    led.close()

    print("✅ Mock GPIO test completed")


async def test_led_controller():
    """Test LED Controller functionality."""
    print("\n🔧 Testing LED Controller...")

    from src.mqtt_client import GPIOLEDController

    controller = GPIOLEDController(pin=18)

    print("✅ LED Controller initialized")

    # Test short blink
    print("💡 Starting 3-second blink test...")
    await controller.start_blink(duration=3, reset_timer=True)

    # Wait for completion
    await asyncio.sleep(3.5)

    print("💡 Testing timer reset...")
    await controller.start_blink(duration=2, reset_timer=True)
    await asyncio.sleep(1)
    await controller.start_blink(duration=2, reset_timer=True)  # Reset timer
    await asyncio.sleep(2.5)

    controller.cleanup()
    print("✅ LED Controller test completed")


async def test_command_processing():
    """Test command processing functionality."""
    print("\n🔧 Testing Command Processing...")

    from src.mqtt_client import LEDControlClient

    client = LEDControlClient()

    # Test blink command
    command = {
        "action": "blink",
        "pin": 18,
        "duration": 2,
        "message": "Test Alert!",
        "reset_timer": True,
        "timestamp": datetime.now().isoformat(),
    }

    print(f"📨 Processing command: {json.dumps(command, indent=2)}")
    await client.process_command(command)

    # Wait for blink to complete
    await asyncio.sleep(2.5)

    await client.shutdown()
    print("✅ Command processing test completed")


def test_json_serialization():
    """Test JSON command serialization."""
    print("\n🔧 Testing JSON Serialization...")

    # Test basic command
    command = {
        "action": "blink",
        "pin": 18,
        "duration": 300,
        "message": "Lightning Alert! ⚡🌩️",
        "timestamp": datetime.now().isoformat(),
        "reset_timer": True,
    }

    # Serialize
    json_str = json.dumps(command, ensure_ascii=False)
    print(f"📝 Serialized command: {json_str}")

    # Deserialize
    parsed = json.loads(json_str)
    print(f"📖 Parsed command: {parsed}")

    assert parsed["action"] == "blink"
    assert parsed["pin"] == 18
    assert "⚡" in parsed["message"]

    print("✅ JSON serialization test completed")


async def test_server_client_simulation():
    """Simulate server-client communication without MQTT."""
    print("\n🔧 Testing Server-Client Simulation...")

    from src.mqtt_client import LEDControlClient

    # Create client
    client = LEDControlClient()

    # Simulate multiple server commands
    commands = [
        {
            "action": "blink",
            "pin": 18,
            "duration": 3,
            "message": "First Alert",
            "reset_timer": True,
            "timestamp": datetime.now().isoformat(),
        },
        {
            "action": "blink",
            "pin": 18,
            "duration": 5,
            "message": "Second Alert (Timer Reset)",
            "reset_timer": True,
            "timestamp": datetime.now().isoformat(),
        },
    ]

    for i, command in enumerate(commands, 1):
        print(f"📨 Sending command {i}: {command['message']}")
        await client.process_command(command)

        if i == 1:
            # Wait 1 second then send reset command
            await asyncio.sleep(1)
            print("🔄 Sending timer reset command...")

    # Wait for final completion
    await asyncio.sleep(6)

    await client.shutdown()
    print("✅ Server-Client simulation completed")


async def main():
    """Run all tests."""
    print("🚀 Starting GPIO LED System Tests")
    print("=" * 50)

    try:
        # Test 1: Mock GPIO
        test_mock_gpio()

        # Test 2: LED Controller
        await test_led_controller()

        # Test 3: Command Processing
        await test_command_processing()

        # Test 4: JSON Serialization
        test_json_serialization()

        # Test 5: Server-Client Simulation
        await test_server_client_simulation()

        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")
        print("\n📖 Next Steps:")
        print(
            "   1. Set up MQTT broker: docker-compose -f docker-compose-client.yml up -d mqtt-broker"
        )
        print("   2. Start client: python src/mqtt_client.py")
        print(
            "   3. Send command: python src/mqtt_server.py --message 'Lightning Alert!'"
        )

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
