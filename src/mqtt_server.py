#!/usr/bin/env python3
"""
MQTT Server for GPIO LED Control

Sends commands to Raspberry Pi clients to blink GPIO LED (pin 18) for 5 minutes.
If the script is run again within 5 minutes, the timer resets.
"""

import asyncio
import logging
import json
from datetime import datetime
import argparse

try:
    from aiomqtt import Client as MQTTClient
except ImportError:
    # Fallback to paho-mqtt for compatibility
    import paho.mqtt.client as mqtt_client

    MQTTClient = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class LEDControlServer:
    """MQTT server for sending LED blink commands to Raspberry Pi clients."""

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        topic: str = "rpi/led/control",
        client_id: str = "led_server",
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.client_id = client_id
        self.blink_duration = 300  # 5 minutes in seconds

    async def send_blink_command(self, message: str = "Lightning Alert!"):
        """Send LED blink command to all subscribed clients."""
        command = {
            "action": "blink",
            "pin": 18,
            "duration": self.blink_duration,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "reset_timer": True,
        }

        command_json = json.dumps(command)

        if MQTTClient:
            # Use asyncio-mqtt if available
            await self._send_with_asyncio_mqtt(command_json)
        else:
            # Fallback to paho-mqtt
            await self._send_with_paho_mqtt(command_json)

    async def _send_with_asyncio_mqtt(self, command_json: str):
        """Send command using asyncio-mqtt client."""
        try:
            async with MQTTClient(
                hostname=self.broker_host,
                port=self.broker_port,
                identifier=self.client_id,
            ) as client:
                await client.publish(self.topic, command_json, qos=1)
                logger.info(
                    f"✅ Command sent via asyncio-mqtt: {command_json}"
                )

        except Exception as e:
            logger.error(f"❌ Failed to send command via asyncio-mqtt: {e}")
            raise

    async def _send_with_paho_mqtt(self, command_json: str):
        """Send command using paho-mqtt client (synchronous fallback)."""

        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                logger.info("Connected to MQTT broker")
                client.publish(self.topic, command_json, qos=1)
                logger.info(f"✅ Command sent via paho-mqtt: {command_json}")
            else:
                logger.error(f"Failed to connect to MQTT broker: {reason_code}")

        def on_publish(client, userdata, mid):
            logger.info("Message published successfully")
            client.disconnect()

        try:
            # Use CallbackAPIVersion.VERSION2 for paho-mqtt 2.0+ compatibility
            client = mqtt_client.Client(client_id=self.client_id, callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2)
            client.on_connect = on_connect
            client.on_publish = on_publish

            client.connect(self.broker_host, self.broker_port, 60)
            client.loop_start()
            await asyncio.sleep(2)  # Give time for message to send
            client.loop_stop()

        except Exception as e:
            logger.error(f"❌ Failed to send command via paho-mqtt: {e}")
            raise


async def main():
    """Main function to run the LED control server."""
    parser = argparse.ArgumentParser(
        description="Send LED blink commands to Raspberry Pi clients"
    )
    parser.add_argument(
        "--broker",
        default="localhost",
        help="MQTT broker hostname (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)",
    )
    parser.add_argument(
        "--topic",
        default="rpi/led/control",
        help="MQTT topic (default: rpi/led/control)",
    )
    parser.add_argument(
        "--message",
        default="Lightning Alert!",
        help="Alert message (default: Lightning Alert!)",
    )
    parser.add_argument(
        "--client-id",
        default="led_server",
        help="MQTT client ID (default: led_server)",
    )

    args = parser.parse_args()

    server = LEDControlServer(
        broker_host=args.broker,
        broker_port=args.port,
        topic=args.topic,
        client_id=args.client_id,
    )

    try:
        logger.info("🚀 Starting LED Control Server...")
        logger.info(f"📡 Broker: {args.broker}:{args.port}")
        logger.info(f"📢 Topic: {args.topic}")
        logger.info("💡 Sending LED blink command (5 minutes duration)...")

        await server.send_blink_command(args.message)

        logger.info("✅ LED blink command sent successfully!")
        logger.info("🔄 If run again within 5 minutes, timer will reset")

    except Exception as e:
        logger.error(f"❌ Failed to send LED command: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
