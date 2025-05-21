import xml.etree.ElementTree as ET

def parse_txt(file_path):
    with open(file_path, 'r') as f:
        lines = [line.strip().split() for line in f if line.strip()]
    headers = lines[0]
    devices = [dict(zip(headers, line)) for line in lines[1:]]
    return devices

def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    devices = {}
    for device in root.findall('device'):
        dev_data = {child.tag: child.text for child in device}
        devices[dev_data['name']] = (device, dev_data)
    return tree, root, devices

def update_or_add_devices(txt_devices, xml_tree, xml_root, xml_devices):
    for txt_device in txt_devices:
        name = txt_device['name']
        if name in xml_devices:
            xml_element, xml_data = xml_devices[name]
            updated = False
            for key, value in txt_device.items():
                if xml_data.get(key) != value:
                    if xml_element.find(key) is not None:
                        xml_element.find(key).text = value
                        updated = True
                    else:
                        new_el = ET.SubElement(xml_element, key)
                        new_el.text = value
                        updated = True
            if updated:
                print(f"Updated: {name}")
        else:
            # Add new device
            device_el = ET.SubElement(xml_root, 'device')
            for key, value in txt_device.items():
                sub_el = ET.SubElement(device_el, key)
                sub_el.text = value
            print(f"Added: {name}")
    return xml_tree

def main(txt_path, xml_path, output_path):
    txt_devices = parse_txt(txt_path)
    xml_tree, xml_root, xml_devices = parse_xml(xml_path)
    updated_tree = update_or_add_devices(txt_devices, xml_tree, xml_root, xml_devices)
    updated_tree.write(output_path, encoding='utf-8', xml_declaration=True)
    print(f"Output saved to {output_path}")

# Example usage
main('devices.txt', 'devices.xml', 'updated_devices.xml')
