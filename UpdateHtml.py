import os
import json
import re
from uuid import uuid4

# Sample data for testing (replace with your actual data)
device_data = [
    ["192.168.1.10", "00:1A:2B:3C:4D:5E", 10, 1, "192.168.1.100", "PC1"],
    ["192.168.1.11", "00:1A:2B:3C:4D:5F", 20, 3, "192.168.1.100", "Server1"],
    ["192.168.1.12", "00:1A:2B:3C:4D:60", 30, 49, "192.168.1.100", "SFP1"],
    ["192.168.1.13", "00:1A:2B:3C:4D:61", 40, 51, "192.168.1.100", "SFP2"],
    ["192.168.1.14", "00:1A:2B:3C:4D:62", 10, 52, "192.168.1.100", "SFP3"],
    ["192.168.2.10", "00:1A:2B:3C:4D:63", 10, 1, "192.168.1.101", "PC2"],
    ["0.0.0.0", None, None, 0, "0.0.0.0", None]  # Example of no data
]

switch_info = [
    ["192.168.1.100", "Switch 1: Core Switch, Location: Data Center 1"],
    ["192.168.1.101", "Switch 2: Edge Switch, Location: Office 2"]
]

# HTML template with escaped curly braces
html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Switch Port Visualizer</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            background-color: #f0f0f0;
            margin: 0;
            padding: 20px;
        }}
        h1 {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
        }}
        .layout-container {{
            margin-bottom: 40px;
        }}
        .layout-title {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            text-align: center;
        }}
        .port-grid {{
            display: grid;
            grid-template-columns: repeat(12, 40px);
            gap: 5px;
            background-color: #333;
            padding: 10px;
            border-radius: 5px;
        }}
        .port {{
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
            border: 1px solid #000;
            box-sizing: border-box;
            position: relative;
        }}
        .port-used {{
            background-color: #28a745;
        }}
        .port-unused {{
            background-color: #6c757d;
        }}
        .vlan-10 {{ background-color: #007bff; }}
        .vlan-20 {{ background-color: #dc3545; }}
        .vlan-30 {{ background-color: #ffc107; }}
        .vlan-40 {{ background-color: #17a2b8; }}
        .vlan-unknown {{ background-color: #6c757d; }}
        .sfp-port {{
            border: 2px solid #ffd700;
        }}
        .tooltip {{
            visibility: hidden;
            width: 200px;
            background-color: #333;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 5px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            transform: translateX(-50%);
            opacity: 0;
            transition: opacity 0.3s;
        }}
        .port:hover .tooltip {{
            visibility: visible;
            opacity: 1;
        }}
        #additional-info {{
            margin-top: 20px;
            padding: 10px;
            background-color: #fff;
            border: 1px solid #ccc;
            border-radius: 5px;
            width: 100%;
            max-width: 600px;
            white-space: pre-wrap;
        }}
    </style>
</head>
<body>
    <h1 id="switch-ip">Switch IP: {switch_ip}</h1>

    <div class="layout-container">
        <div class="layout-title">Port Usage Layout</div>
        <div id="usage-layout" class="port-grid"></div>
    </div>

    <div class="layout-container">
        <div class="layout-title">VLAN Layout</div>
        <div id="vlan-layout" class="port-grid"></div>
    </div>

    <div id="additional-info">
        <h2>Additional Information</h2>
        <p>{additional_info}</p>
    </div>

    <script>
        const switchData = {switch_data};

        function populateLayouts() {{
            const usageLayout = document.getElementById('usage-layout');
            const vlanLayout = document.getElementById('vlan-layout');
            const switchIp = document.getElementById('switch-ip');

            switchIp.textContent = `Switch IP: ${{switchData.switch_ip}}`;

            for (let i = 1; i <= 52; i++) {{
                const portData = switchData.ports.find(p => p.port === i) || {{
                    port: i,
                    used: false,
                    vlan: null,
                    device: null,
                    mac: null,
                    is_sfp: i > 48
                }};

                const usagePort = document.createElement('div');
                usagePort.className = `port ${{portData.used ? 'port-used' : 'port-unused'}} ${{portData.is_sfp ? 'sfp-port' : ''}}`;
                usagePort.textContent = portData.port;
                usageLayout.appendChild(usagePort);

                const vlanPort = document.createElement('div');
                const vlanClass = portData.vlan ? `vlan-${{portData.vlan}}` : 'vlan-unknown';
                vlanPort.className = `port ${{vlanClass}} ${{portData.is_sfp ? 'sfp-port' : ''}}`;
                vlanPort.textContent = portData.port;

                if (portData.device && portData.mac) {{
                    const tooltip = document.createElement('div');
                    tooltip.className = 'tooltip';
                    tooltip.textContent = `Device: ${{portData.device}}\\nMAC: ${{portData.mac}}`;
                    vlanPort.appendChild(tooltip);
                }}

                vlanLayout.appendChild(vlanPort);
            }}
        }}

        populateLayouts();
    </script>
</body>
</html>
"""


def read_existing_html(file_path):
    """Read the switchData JSON from an existing HTML file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            # Extract JSON from the script tag
            match = re.search(r'const switchData = (\{[\s\S]*?\});', content)
            if match:
                return json.loads(match.group(1))
    except (FileNotFoundError, json.JSONDecodeError, re.error):
        return None
    return None


def generate_switch_html(device_data, switch_info):
    # Group devices by switch IP
    switches = set(data[4] for data in device_data if data[4] != "0.0.0.0")

    for switch_ip in switches:
        # Filter device data for this switch
        switch_devices = [data for data in device_data if data[4] == switch_ip and data[3] != 0]

        # Read existing HTML file
        file_path = f"C:\\{switch_ip}\\{switch_ip}.html"
        existing_data = read_existing_html(file_path) or {
            "switch_ip": switch_ip,
            "ports": [{"port": i, "used": False, "vlan": None, "device": None, "mac": None, "is_sfp": i > 48} for i in
                      range(1, 53)]
        }

        # Create new ports data
        new_ports = existing_data["ports"].copy()  # Start with existing ports
        needs_update = False

        # Update ports based on device_data
        for device in switch_devices:
            port_num = device[3]
            if port_num < 1 or port_num > 52:
                continue  # Skip invalid ports
            port_idx = port_num - 1  # 0-based index for list
            new_port_data = {
                "port": port_num,
                "used": bool(device[5] or device[0] != "0.0.0.0"),
                "vlan": device[2] if device[2] else None,
                "device": device[5] if device[5] else None,
                "mac": device[1] if device[1] else None,
                "is_sfp": port_num > 48
            }

            # Compare with existing port data
            existing_port = new_ports[port_idx]
            if (existing_port["used"] != new_port_data["used"] or
                    existing_port["vlan"] != new_port_data["vlan"] or
                    existing_port["device"] != new_port_data["device"] or
                    existing_port["mac"] != new_port_data["mac"]):
                new_ports[port_idx] = new_port_data
                needs_update = True

        # Get additional info for this switch
        additional_info = next((info[1] for info in switch_info if info[0] == switch_ip),
                               "No additional information available.")

        # Only write file if there's an update
        if needs_update:
            switch_data = {
                "switch_ip": switch_ip,
                "ports": new_ports
            }

            # Format HTML with switch data
            html_content = html_template.format(
                switch_ip=switch_ip,
                switch_data=json.dumps(switch_data, indent=2),
                additional_info=additional_info
            )

            # Create directory if it doesn't exist
            directory = f"C:\\{switch_ip}"
            os.makedirs(directory, exist_ok=True)

            # Write HTML file
            with open(file_path, 'w') as f:
                f.write(html_content)

            print(f"Updated HTML file for switch {switch_ip} at {file_path}")
        else:
            print(f"No updates needed for switch {switch_ip}")


# Run the function
generate_switch_html(device_data, switch_info)
