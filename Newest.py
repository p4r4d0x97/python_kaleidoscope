import xml.etree.ElementTree as ET

def update_xml_from_list(xml_file, data_list):
    tree = ET.parse(xml_file)
    root = tree.getroot()  # Root is <Network>
    
    # Loop through each entry in the data_list
    for data in data_list:
        ip, mac, vlan, port, switch, device_name, html_path, url = data
        
        # Skip the entry if ip address is 0 (no data)
        if ip == 0:
            continue

        # Find the corresponding Device element based on ip address (assuming ip is unique in XML)
        device = find_device_by_ip(root, ip)
        
        if device is not None:
            # Update the device fields in the XML
            update_or_create_tag(device, 'Mac', mac)
            update_or_create_tag(device, 'Vlan', vlan)
            update_or_create_tag(device, 'Port', port)
            update_or_create_tag(device, 'Switch', switch)
            update_or_create_tag(device, 'Name', device_name)
            update_or_create_tag(device, 'Html', html_path)
            update_or_create_tag(device, 'Url', url)
        else:
            # If no matching device found, add a new one
            new_device = ET.Element('Device')
            update_or_create_tag(new_device, 'Ip', ip)
            update_or_create_tag(new_device, 'Mac', mac)
            update_or_create_tag(new_device, 'Vlan', vlan)
            update_or_create_tag(new_device, 'Port', port)
            update_or_create_tag(new_device, 'Switch', switch)
            update_or_create_tag(new_device, 'Name', device_name)
            update_or_create_tag(new_device, 'Html', html_path)
            update_or_create_tag(new_device, 'Url', url)
            
            # Append the new device to the Network root
            root.append(new_device)

    # Write the changes back to the XML file
    tree.write(xml_file)

def update_or_create_tag(parent, tag_name, value):
    """Helper function to update an existing tag or create a new one if necessary."""
    if value == 0:  # Skip if the value is 0
        return
    
    tag = parent.find(tag_name)
    if tag is not None:
        if tag.text != str(value):  # Only update if the value is different
            tag.text = str(value)
    else:
        # Create a new tag if it doesn't exist
        new_tag = ET.Element(tag_name)
        new_tag.text = str(value) if value != 0 else ""  # Set empty string if value is 0
        parent.append(new_tag)

def find_device_by_ip(root, ip):
    """Helper function to find a device by its IP address in the XML."""
    for device in root.findall('Device'):
        ip_tag = device.find('Ip')
        if ip_tag is not None and ip_tag.text == str(ip):
            return device
    return None

# Example usage
data_list = [
    [ "192.168.1.1", "00:11:22:33:44:55", 10, 1, "Switch1", "DeviceA", "path/to/html", "http://example.com"],
    [ "192.168.1.2", "00:11:22:33:44:66", 0, 0, "Switch2", "DeviceB", "path/to/html", "http://example2.com"],
    [ "192.168.1.3", "00:11:22:33:44:77", 0, 0, "Switch3", "DeviceC", "", ""],
    # Add more entries as needed
]

xml_file = "network.xml"
update_xml_from_list(xml_file, data_list)
