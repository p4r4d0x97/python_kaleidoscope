import binascii

# --- Checksum & CRC functions ---

def crc16_ccitt_false(data):
    crc = 0xFFFF
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if (crc & 0x8000):
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

def crc16_xmodem(data):
    crc = 0x0000
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if (crc & 0x8000):
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

def crc16_modbus(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if (crc & 0x0001):
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

def crc32(data):
    return binascii.crc32(data) & 0xFFFFFFFF

def crc8(data, poly=0x07, init=0x00):
    crc = init
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ poly) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc

# --- Checksum matching logic ---

def try_checksums(packet_bytes):
    packet_len = len(packet_bytes)
    results = []

    if packet_len < 3:
        return ["Packet too short."]

    for offset in range(packet_len - 2, packet_len - 1):  # Tail 2 bytes
        data = packet_bytes[:offset]
        tail = packet_bytes[offset:]
        tail_be = int.from_bytes(tail, 'big')
        tail_le = int.from_bytes(tail, 'little')

        checks = [
            ("CRC16-CCITT (False)", crc16_ccitt_false(data)),
            ("CRC16-XModem", crc16_xmodem(data)),
            ("CRC16-MODBUS", crc16_modbus(data)),
            ("CRC32", crc32(data) & 0xFFFF),  # last 2 bytes only
            ("CRC8", crc8(data)),
            ("Simple Sum mod 65536", sum(data) & 0xFFFF),
            ("Simple Sum mod 256", sum(data) & 0xFF),
        ]

        for name, val in checks:
            if val == tail_be:
                results.append(f"✅ Match ({name}) — Big Endian at offset {offset}")
            elif val == tail_le:
                results.append(f"✅ Match ({name}) — Little Endian at offset {offset}")

    if not results:
        results.append("❌ No known checksum match found.")

    return results

# --- Entry point ---

def analyze_packet(hex_str):
    hex_str = hex_str.strip().replace(" ", "")
    try:
        packet = bytes.fromhex(hex_str)
    except ValueError:
        print(f"❌ Invalid hex: {hex_str}")
        return

    print(f"\n📦 Analyzing Packet: {hex_str}")
    print(f"Length: {len(packet)} bytes")
    results = try_checksums(packet)
    for res in results:
        print(res)

# --- Example usage with your packets ---

if __name__ == "__main__":
    test_packets = [
        "05a0ba44ba3df20e001001076b290d618000800000049d",
        "05a0ba44ba3df20e0010010c7ed03d00ff00000000961e",
        "05a0ba44ba3df20e0010010d68822d00ff80ff0000fe9c"
    ]

    for hex_packet in test_packets:
        analyze_packet(hex_packet)

    # Optional: input more
    while True:
        user = input("\nEnter a hex packet to test (or 'q' to quit): ").strip()
        if user.lower() == 'q':
            break
        analyze_packet(user)
