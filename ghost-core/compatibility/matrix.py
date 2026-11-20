"""Ghost-OS Compatibility Matrix Generator.

Maps subsystem probing capabilities across Windows (WMI/SetupAPI/smartctl)
and Linux (sysfs/procfs/dmidecode/lshw/smartctl).
"""

from typing import Dict
from ghost_core.schemas.scan import ModuleCompatibility, PlatformEnum


class CompatibilityEvaluator:
    """Generates and evaluates platform module capability status."""

    @classmethod
    def evaluate_capabilities(
        cls,
        platform: PlatformEnum,
        is_admin: bool = True,
        has_smartctl: bool = True,
    ) -> Dict[str, ModuleCompatibility]:
        matrix: Dict[str, ModuleCompatibility] = {
            "cpu": ModuleCompatibility.SUPPORTED,
            "ram": ModuleCompatibility.SUPPORTED,
            "gpu": ModuleCompatibility.SUPPORTED,
            "motherboard": ModuleCompatibility.SUPPORTED,
            "network": ModuleCompatibility.SUPPORTED,
        }

        # Storage SMART
        if not has_smartctl and not is_admin:
            matrix["storage_smart"] = ModuleCompatibility.PERMISSION_DENIED
        elif has_smartctl:
            matrix["storage_smart"] = ModuleCompatibility.SUPPORTED
        else:
            matrix["storage_smart"] = ModuleCompatibility.LIMITED

        # Battery
        matrix["battery"] = ModuleCompatibility.SUPPORTED

        # Thermals
        if platform == PlatformEnum.WINDOWS:
            # Under Windows, non-admin WMI has limited thermal access without ring-0 drivers
            matrix["thermals"] = ModuleCompatibility.SUPPORTED if is_admin else ModuleCompatibility.LIMITED
            matrix["fans"] = ModuleCompatibility.LIMITED
        else:
            # Linux hwmon / sensors
            matrix["thermals"] = ModuleCompatibility.SUPPORTED
            matrix["fans"] = ModuleCompatibility.SUPPORTED if is_admin else ModuleCompatibility.LIMITED

        return matrix
