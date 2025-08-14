import asyncio
import os
import ipaddress
from asyncio.subprocess import PIPE
import platform

# Ping Command based on OS
def get_ping_command(ip):
    # Windows uses `ping -n` and Unix-based systems use `ping -c`
    if platform.system().lower() == "windows":
        return ['ping', '-n', '1', '-w', '1000', ip]
    else:
        return ['ping', '-c', '1', '-W', '1', ip]

async def ping(ip):
    # Use subprocess to ping IP asynchronously
    process = await asyncio.create_subprocess_exec(
        *get_ping_command(ip), stdout=PIPE, stderr=PIPE
    )
    stdout, stderr = await process.communicate()
    
    # Check if the ping was successful
    if process.returncode == 0:
        print(f"{ip} is online")
    else:
        # Uncomment the next line to debug failed pings
        # print(f"Failed to ping {ip}: {stderr.decode()}")
        pass

async def run_pings_for_vlan(subnet):
    # Generate all IPs in the subnet except the gateway and broadcast
    network = ipaddress.IPv4Network(subnet, strict=False)
    
    # Exclude the network address, gateway, and broadcast address
    gateway = network.network_address + 1  # The first address is the gateway
    broadcast = network.broadcast_address

    tasks = []
    for ip in network.hosts():
        if ip != gateway and ip != broadcast:
            tasks.append(ping(str(ip)))
    
    # Run all ping tasks concurrently
    await asyncio.gather(*tasks)

async def main():
    # List of VLANs (subnets to scan)
    vlans = [
        '192.168.1.0/24',  # Vlan 10
        '192.168.2.0/24',  # Vlan 20
        # Add more VLANs as needed
    ]
    
    # Ping all IPs in each VLAN
    tasks = [run_pings_for_vlan(vlan) for vlan in vlans]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
