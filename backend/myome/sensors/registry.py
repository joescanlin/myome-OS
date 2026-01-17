"""Sensor adapter registry and factory"""

from myome.sensors.base import HealthSensor, MultiSensorDevice, SensorType


class SensorRegistry:
    """Registry of available sensor adapters"""

    _adapters: dict[str, type[HealthSensor]] = {}
    _multi_device_adapters: dict[str, type[MultiSensorDevice]] = {}

    @classmethod
    def register(cls, vendor: str, sensor_type: SensorType):
        """Decorator to register a sensor adapter"""

        def decorator(adapter_class: type[HealthSensor]):
            key = f"{vendor}:{sensor_type.value}"
            cls._adapters[key] = adapter_class
            return adapter_class

        return decorator

    @classmethod
    def register_device(cls, vendor: str):
        """Decorator to register a multi-sensor device adapter"""

        def decorator(adapter_class: type[MultiSensorDevice]):
            cls._multi_device_adapters[vendor] = adapter_class
            return adapter_class

        return decorator

    @classmethod
    def get_adapter(
        cls,
        vendor: str,
        sensor_type: SensorType,
    ) -> type[HealthSensor] | None:
        """Get adapter class for vendor and sensor type"""
        key = f"{vendor}:{sensor_type.value}"
        return cls._adapters.get(key)

    @classmethod
    def get_device_adapter(cls, vendor: str) -> type[MultiSensorDevice] | None:
        """Get multi-sensor device adapter for vendor"""
        return cls._multi_device_adapters.get(vendor)

    @classmethod
    def list_adapters(cls) -> list[str]:
        """List all registered adapters"""
        return list(cls._adapters.keys())

    @classmethod
    def list_device_adapters(cls) -> list[str]:
        """List all registered device adapters"""
        return list(cls._multi_device_adapters.keys())
