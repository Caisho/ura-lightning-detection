#!/usr/bin/env python3
"""
MQTT Client for Raspberry Pi GPIO LED Control

Listens for MQTT commands and controls GPIO LED (pin 18) for specified duration.
Supports timer reset functionality when new commands are received.
"""

import asyncio
import logging
import json
import signal
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import argparse

try:
    from aiomqtt import Client as MQTTClient
except ImportError:
    # Fallback to paho-mqtt for compatibility
    import paho.mqtt.client as mqtt_client

    MQTTClient = None

# GPIO imports with fallback for non-Raspberry Pi environments
try:
    from gpiozero import LED

    GPIO_AVAILABLE = True
except ImportError:
    try:
        import RPi.GPIO as GPIO

        GPIO_AVAILABLE = True
    except ImportError:
        # Mock GPIO for testing on non-RPi systems
        GPIO_AVAILABLE = False
        logging.warning(
            "GPIO libraries not available. Using mock GPIO for testing."
        )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MockLED:
    """Mock LED class for testing on non-Raspberry Pi systems."""

    def __init__(self, pin: int):
        self.pin = pin
        self.is_lit = False
        logger.info(f"🔄 Mock LED created on pin {pin}")

    def on(self):
        """Turn on the mock LED."""
        self.is_lit = True
        logger.info(f"💡 Mock LED on pin {self.pin} turned ON")

    def off(self):
        """Turn off the mock LED."""
        self.is_lit = False
        logger.info(f"💡 Mock LED on pin {self.pin} turned OFF")

    def blink(
        self,
        on_time: float = 1,
        off_time: float = 1,
        n: Optional[int] = None,
        background: bool = True,
    ):
        """Mock blink method."""
        logger.info(
            f"💡 Mock LED on pin {self.pin} blinking: on={on_time}s, off={off_time}s, n={n}, bg={background}"
        )

    def close(self):
        """Close mock LED."""
        logger.info(f"🔄 Mock LED on pin {self.pin} closed")


class GPIOLEDController:
    """Controls GPIO LED with timer functionality."""

    def __init__(self, pin: int = 18):
        self.pin = pin
        self.led = None
        self.blink_task: Optional[asyncio.Task] = None
        self.current_end_time: Optional[datetime] = None
        self.is_running = False

        # Initialize LED
        self._init_led()

    def _init_led(self):
        """Initialize the LED object based on available libraries."""
        if GPIO_AVAILABLE:
            try:
                # Try gpiozero first (modern approach)
                self.led = LED(self.pin)
                logger.info(
                    f"✅ GPIO LED initialized on pin {self.pin} using gpiozero"
                )
            except Exception:
                try:
                    # Fallback to RPi.GPIO
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup(self.pin, GPIO.OUT)
                    self.led = None  # Will use GPIO directly
                    logger.info(
                        f"✅ GPIO LED initialized on pin {self.pin} using RPi.GPIO"
                    )
                except Exception as e2:
                    logger.error(f"❌ Failed to initialize GPIO: {e2}")
                    self.led = MockLED(self.pin)
        else:
            self.led = MockLED(self.pin)

    async def start_blink(self, duration: int, reset_timer: bool = True):
        """Start LED blinking for specified duration in seconds."""
        now = datetime.now()
        new_end_time = now + timedelta(seconds=duration)

        # Check if we should reset the timer
        if reset_timer and self.current_end_time:
            if now < self.current_end_time:
                logger.info(
                    "🔄 Resetting timer - new command received within active period"
                )
                await self.stop_blink()

        self.current_end_time = new_end_time

        # Start new blink task
        self.blink_task = asyncio.create_task(self._blink_routine(duration))
        logger.info(
            f"💡 LED blink started for {duration} seconds (until {new_end_time.strftime('%H:%M:%S')})"
        )

    async def _blink_routine(self, duration: int):
        """LED blinking routine."""
        try:
            self.is_running = True
            end_time = datetime.now() + timedelta(seconds=duration)

            logger.info(
                f"🟢 Starting LED blink routine for {duration} seconds"
            )

            while datetime.now() < end_time:
                # Turn LED on
                await self._turn_on()
                await asyncio.sleep(0.5)  # On for 0.5 seconds

                # Turn LED off
                await self._turn_off()
                await asyncio.sleep(0.5)  # Off for 0.5 seconds

                # Check if we should stop early
                if not self.is_running:
                    break

            # Ensure LED is off when done
            await self._turn_off()
            logger.info("🔴 LED blink routine completed")

        except asyncio.CancelledError:
            await self._turn_off()
            logger.info("🔴 LED blink routine cancelled")
        except Exception as e:
            logger.error(f"❌ Error in LED blink routine: {e}")
        finally:
            self.is_running = False
            if datetime.now() >= self.current_end_time:
                self.current_end_time = None

    async def _turn_on(self):
        """Turn LED on."""
        if hasattr(self.led, "on"):
            self.led.on()
        elif self.led is None:  # Using RPi.GPIO directly
            GPIO.output(self.pin, GPIO.HIGH)

    async def _turn_off(self):
        """Turn LED off."""
        if hasattr(self.led, "off"):
            self.led.off()
        elif self.led is None:  # Using RPi.GPIO directly
            GPIO.output(self.pin, GPIO.LOW)

    async def stop_blink(self):
        """Stop current LED blinking."""
        if self.blink_task and not self.blink_task.done():
            self.is_running = False
            self.blink_task.cancel()
            try:
                await self.blink_task
            except asyncio.CancelledError:
                pass

        await self._turn_off()
        logger.info("🛑 LED blink stopped")

    def cleanup(self):
        """Cleanup GPIO resources."""
        try:
            if hasattr(self.led, "close"):
                self.led.close()
            elif GPIO_AVAILABLE and self.led is None:
                GPIO.cleanup()
            logger.info("🧹 GPIO cleanup completed")
        except Exception as e:
            logger.error(f"⚠️ Error during GPIO cleanup: {e}")


class LEDControlClient:
    """MQTT client for receiving LED control commands."""

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        topic: str = "rpi/led/control",
        client_id: str = "led_client",
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.client_id = client_id
        self.led_controller = GPIOLEDController()
        self.running = True

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"📶 Received signal {signum}, shutting down...")
        self.running = False

    async def process_command(self, command: Dict[str, Any]):
        """Process received LED control command."""
        try:
            action = command.get("action")
            pin = command.get("pin", 18)
            duration = command.get("duration", 300)
            message = command.get("message", "Alert")
            reset_timer = command.get("reset_timer", True)
            timestamp = command.get("timestamp", datetime.now().isoformat())

            logger.info(
                f"📨 Received command: {action} on pin {pin} for {duration}s"
            )
            logger.info(f"💬 Message: {message}")
            logger.info(f"⏰ Timestamp: {timestamp}")

            if action == "blink":
                await self.led_controller.start_blink(duration, reset_timer)
            else:
                logger.warning(f"⚠️ Unknown action: {action}")

        except Exception as e:
            logger.error(f"❌ Error processing command: {e}")

    async def start_client(self):
        """Start the MQTT client and listen for commands."""
        if MQTTClient:
            await self._start_with_asyncio_mqtt()
        else:
            await self._start_with_paho_mqtt()

    async def _start_with_asyncio_mqtt(self):
        """Start client using asyncio-mqtt."""
        try:
            async with MQTTClient(
                hostname=self.broker_host,
                port=self.broker_port,
                identifier=self.client_id,
            ) as client:
                await client.subscribe(self.topic)
                logger.info(
                    f"📡 Connected to MQTT broker at {self.broker_host}:{self.broker_port}"
                )
                logger.info(f"👂 Listening on topic: {self.topic}")

                async for message in client.messages:
                    if not self.running:
                        break

                    try:
                        command = json.loads(message.payload.decode())
                        await self.process_command(command)
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid JSON received: {e}")
                    except Exception as e:
                        logger.error(f"❌ Error processing message: {e}")

        except Exception as e:
            logger.error(f"❌ MQTT client error: {e}")
            raise

    async def _start_with_paho_mqtt(self):
        """Start client using paho-mqtt (fallback)."""

        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                logger.info(
                    f"📡 Connected to MQTT broker at {self.broker_host}:{self.broker_port}"
                )
                client.subscribe(self.topic)
                logger.info(f"👂 Listening on topic: {self.topic}")
            else:
                logger.error(f"❌ Failed to connect to MQTT broker: {reason_code}")

        def on_message(client, userdata, msg):
            try:
                command = json.loads(msg.payload.decode())
                # Run async command processing in event loop
                asyncio.create_task(self.process_command(command))
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON received: {e}")
            except Exception as e:
                logger.error(f"❌ Error processing message: {e}")

        try:
            # Use CallbackAPIVersion.VERSION2 for paho-mqtt 2.0+ compatibility
            client = mqtt_client.Client(client_id=self.client_id, callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2)
            client.on_connect = on_connect
            client.on_message = on_message

            client.connect(self.broker_host, self.broker_port, 60)
            client.loop_start()

            # Keep running until shutdown signal
            while self.running:
                await asyncio.sleep(1)

            client.loop_stop()
            client.disconnect()

        except Exception as e:
            logger.error(f"❌ MQTT client error: {e}")
            raise

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("🛑 Shutting down LED control client...")
        self.running = False
        await self.led_controller.stop_blink()
        self.led_controller.cleanup()


async def main():
    """Main function to run the LED control client."""
    parser = argparse.ArgumentParser(
        description="MQTT client for Raspberry Pi GPIO LED control"
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
        "--client-id",
        default="led_client",
        help="MQTT client ID (default: led_client)",
    )

    args = parser.parse_args()

    client = LEDControlClient(
        broker_host=args.broker,
        broker_port=args.port,
        topic=args.topic,
        client_id=args.client_id,
    )

    try:
        logger.info("🚀 Starting LED Control Client...")
        logger.info(f"📡 Broker: {args.broker}:{args.port}")
        logger.info(f"📢 Topic: {args.topic}")
        logger.info("💡 Ready to receive LED control commands...")

        await client.start_client()

    except KeyboardInterrupt:
        logger.info("📶 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Client error: {e}")
        return 1
    finally:
        await client.shutdown()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
