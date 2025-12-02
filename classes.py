import json

# -------------------------------
# DEVICE CLASS
# -------------------------------
class Device:
    def __init__(self, ip, mac, vlan):
        self.ip = ip
        self.mac = mac
        self.vlan = vlan
        self.tags = set()  # store tags like "vlan10", "vendor_AAA", "printer"

    # Runs all check modules on this device
    def run_checks(self, checks):
        for check in checks:
            check.apply(self)

    # Convert to dict for JSON export
    def to_dict(self):
        return {
            "ip": self.ip,
            "mac": self.mac,
            "vlan": self.vlan,
            "tags": sorted(list(self.tags))
        }

# -------------------------------
# CHECK MODULES
# -------------------------------

# 1. VLAN check module
class VlanCheck:
    def apply(self, device):
        # Add a tag based on VLAN
        device.tags.add(f"vlan{device.vlan}")

# 2. MAC vendor check module
class MacVendorCheck:
    def apply(self, device):
        # Fake logic for vendor detection based on MAC
        if device.mac.startswith("aa"):
            device.tags.add("vendor_AAA")
        elif device.mac.startswith("bb"):
            device.tags.add("vendor_BBB")
        else:
            device.tags.add("vendor_unknown")

# 3. Device type check module (PLC, Printer, etc.)
class DeviceTypeCheck:
    def apply(self, device):
        # Dummy logic: if VLAN 10 → PLC, if VLAN 20 → Printer
        if device.vlan == 10:
            device.tags.add("PLC")
        elif device.vlan == 20:
            device.tags.add("Printer")
        else:
            device.tags.add("UnknownType")

# -------------------------------
# JSON EXPORT FUNCTION
# -------------------------------
def export_to_json(devices, filename="devices.json"):
    data = [d.to_dict() for d in devices]
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

# -------------------------------
# MAIN SCRIPT
# -------------------------------
if __name__ == "__main__":
    # Dummy firewall data (IP, MAC, VLAN)
    firewall_data = [
        ["192.168.1.10", "aa:aa:aa:aa:aa", 10],
        ["192.168.1.11", "bb:bb:bb:bb:bb", 20],
        ["192.168.1.12", "cc:cc:cc:cc:cc", 10],
    ]

    # Create Device objects from firewall data
    devices = [Device(ip, mac, vlan) for ip, mac, vlan in firewall_data]

    # Create check module objects
    checks = [VlanCheck(), MacVendorCheck(), DeviceTypeCheck()]

    # Run all checks on each device
    for device in devices:
        device.run_checks(checks)

    # Export the results to JSON
    export_to_json(devices)

    print("JSON export completed. Devices and tags:")
    for device in devices:
        print(device.to_dict())
