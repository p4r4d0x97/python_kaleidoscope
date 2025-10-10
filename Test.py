import struct

def parse_iot_packet(hex_input):
    data = bytes.fromhex(hex_input.strip().replace(" ", "").replace(":", ""))
    print(f"Total bytes: {len(data)}")
    print(f"Raw data: {data.hex()}\n")

    # Example parsing: adjust indexes and formats based on your protocol

    # First 4 bytes as unsigned int (device ID)
    if len(data) >= 4:
        device_id = struct.unpack(">I", data[0:4])[0]
        print(f"Device ID (4 bytes, big-endian): {device_id}")
    else:
        print("Not enough data for Device ID (4 bytes)")

    # Next 4 bytes as unsigned int (timestamp)
    if len(data) >= 8:
        timestamp = struct.unpack(">I", data[4:8])[0]
        print(f"Timestamp (4 bytes, big-endian): {timestamp}")
    else:
        print("Not enough data for Timestamp (4 bytes)")

    # Next 2 bytes as unsigned short (sensor value)
    if len(data) >= 10:
        sensor_val = struct.unpack(">H", data[8:10])[0]
        print(f"Sensor Value (2 bytes, big-endian): {sensor_val}")
    else:
        print("Not enough data for Sensor Value (2 bytes)")

    # Next 4 bytes as float (sensor reading)
    if len(data) >= 14:
        try:
            sensor_float = struct.unpack(">f", data[10:14])[0]
            print(f"Sensor Float (4 bytes, big-endian): {sensor_float}")
        except Exception as e:
            print(f"Cannot parse bytes 10-14 as float: {e}")
    else:
        print("Not enough data for Sensor Float (4 bytes)")

    # Remaining bytes as flags or checksum
    if len(data) > 14:
        flags = data[14:]
        print(f"Flags / checksum bytes ({len(flags)} bytes): {flags.hex()}")
    else:
        print("No extra bytes for Flags / Checksum")

if __name__ == "__main__":
    hex_string = input("Enter UDP hex payload: ")
    parse_iot_packet(hex_string)
