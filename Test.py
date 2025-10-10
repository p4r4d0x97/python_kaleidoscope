import sys
import crcmod

def calculate_checksums(data):
    """Calculate various 8-bit checksums for the first 22 bytes."""
    results = {}
    
    # XOR of all bytes
    xor_result = 0
    for b in data[:22]:
        xor_result ^= b
    results['XOR'] = xor_result
    
    # Sum modulo 256
    sum_256 = sum(data[:22]) % 256
    results['Sum mod 256'] = sum_256
    
    # Sum modulo 255
    sum_255 = sum(data[:22]) % 255
    results['Sum mod 255'] = sum_255
    
    # Simple sum (lower 8 bits)
    simple_sum = sum(data[:22]) & 0xFF
    results['Simple sum'] = simple_sum
    
    # CRC-8-CCITT (poly=0x07, init=0x00, xorout=0x00)
    crc8_ccitt = crcmod.predefined.mkCrcFun('crc-8')
    results['CRC-8-CCITT'] = crc8_ccitt(data[:22])
    
    # CRC-8-Dallas/Maxim (poly=0x31, init=0x00, xorout=0x00)
    crc8_dallas = crcmod.mkCrcFun(0x131, initCrc=0x00, xorOut=0x00)
    results['CRC-8-Dallas'] = crc8_dallas(data[:22])
    
    return results

def parse_iot_packet(hex_string):
    try:
        # Convert hex string to bytes
        data = bytes.fromhex(hex_string)
        if len(data) != 23:
            raise ValueError("Input must be a 23-byte hex string (46 characters).")
        
        # Expected header (bytes 0-10)
        expected_header = bytes.fromhex("05 a0 ba 44 ba 3d f2 0e 00 10 01")
        header = data[0:11]
        if header != expected_header:
            print("Warning: Header does not match expected value.")
        
        # Sequence number (byte 11)
        seq = data[11]
        
        # Counter (bytes 12-13, little-endian uint16)
        counter = int.from_bytes(data[12:14], 'little')
        
        # Other value (bytes 14-15, little-endian uint16, possibly RSSI/battery)
        other_value = int.from_bytes(data[14:16], 'little')
        
        # Status byte (byte 16): 0xFF = Pressed, else = Not Pressed
        status_byte = data[16]
        status = "Pressed" if status_byte == 0xFF else "Not Pressed"
        
        # Additional data/flags (bytes 17-21)
        additional_data = data[17:22].hex(' ')
        
        # Checksum (byte 22)
        actual_checksum = data[22]
        
        # Brute-force checksums
        checksums = calculate_checksums(data)
        checksum_valid = "Not verified"
        for method, value in checksums.items():
            if value == actual_checksum:
                checksum_valid = f"Verified with {method}"
                break
        
        # Output in human-readable format
        print("Parsed IoT Packet:")
        print(f"Header: {header.hex(' ')} (fixed identifier)")
        print(f"Sequence Number: 0x{seq:02x} ({seq})")
        print(f"Counter: {counter} (0x{counter:04x})")
        print(f"Other Value: {other_value} (0x{other_value:04x})")
        print(f"Status Byte: 0x{status_byte:02x}")
        print(f"Status: {status}")
        print(f"Additional Data: {additional_data}")
        print(f"Checksum: 0x{actual_checksum:02x} ({checksum_valid})")
        if checksum_valid == "Not verified":
            print("Checksum possibilities:")
            for method, value in checksums.items():
                print(f"  {method}: 0x{value:02x}")
    
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

# Main: Get input from user
if __name__ == "__main__":
    # Install crcmod if needed: pip install crcmod
    if len(sys.argv) > 1:
        hex_input = sys.argv[1]
    else:
        hex_input = input("Enter the 23-byte hex string: ").strip()
    parse_iot_packet(hex_input)
