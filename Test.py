import binascii
import sys

# CRC-16-CCITT-FALSE (poly=0x1021, init=0xFFFF)
def crc16_ccitt(data, poly=0x1021, init=0xFFFF):
    crc = init
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF

# --- Main decoder function ---
def decode_packet(hex_str):
    hex_str = hex_str.strip().replace(" ", "").replace(":", "")
    try:
        data = bytes.fromhex(hex_str)
    except ValueError:
        print("❌ Invalid hex input")
        return

    if len(data) != 23:
        print(f"❌ Invalid packet length: {len(data)} bytes (expected 23)")
        return

    header = data[0:11]
    msg_type = data[11]
    raw_data = data[12:16]
    sensor1 = int.from_bytes(data[16:18], 'little')
    sensor2 = int.from_bytes(data[18:20], 'little')
    reserved = data[20]
    checksum_bytes = data[21:23]
    computed_crc = crc16_ccitt(data[0:21])
    packet_crc = int.from_bytes(checksum_bytes, 'big')

    print("📦 Decoded Packet")
    print("-------------------------")
    print(f"Header         : {header.hex()} (bytes 0-10)")
    print(f"Message Type   : 0x{msg_type:02x} (byte 11)")
    print(f"Raw Data Bytes : {raw_data.hex()} (bytes 12-15)")
    print(f"Sensor 1       : {sensor1} (uint16, little-endian, bytes 16-17)")
    print(f"Sensor 2       : {sensor2} (uint16, little-endian, bytes 18-19)")
    print(f"Reserved Byte  : 0x{reserved:02x} (byte 20)")
    print(f"CRC in Packet  : 0x{packet_crc:04x} (bytes 21-22)")
    print(f"CRC Computed   : 0x{computed_crc:04x} -> {'✅ MATCH' if packet_crc == computed_crc else '❌ MISMATCH'}")

# --- Run decoder ---
if __name__ == "__main__":
    # Example usage: paste a hex string here to decode
    test_packet = "05a0ba44ba3df20e0010010d68822d00ff80ff0000fe9c"
    decode_packet(test_packet)

    # Optional: accept user input
    while True:
        user_input = input("\nEnter another hex packet (or 'q' to quit): ").strip()
        if user_input.lower() == 'q':
            break
        decode_packet(user_input)
