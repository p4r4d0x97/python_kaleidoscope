import sys
import crcmod

def calculate_checksums(data):
    """Calculate 8-bit and 16-bit checksums for different byte ranges."""
    results = {'8bit': {}, '16bit_22_23': {}, '16bit_21_22': {}}
    
    # 8-bit checksums (over bytes 0-22, compare to byte 23)
    bytes_0_22 = data[:22]
    results['8bit']['XOR'] = 0
    for b in bytes_0_22:
        results['8bit']['XOR'] ^= b
    results['8bit']['Sum mod 256'] = sum(bytes_0_22) % 256
    results['8bit']['Sum mod 255'] = sum(bytes_0_22) % 255
    results['8bit']['Simple sum'] = sum(bytes_0_22) & 0xFF
    crc8_ccitt = crcmod.predefined.mkCrcFun('crc-8')
    results['8bit']['CRC-8-CCITT'] = crc8_ccitt(bytes_0_22)
    crc8_dallas = crcmod.mkCrcFun(0x131, initCrc=0x00, xorOut=0x00)
    results['8bit']['CRC-8-Dallas'] = crc8_dallas(bytes_0_22)
    
    # 16-bit checksums (over bytes 0-21, compare to bytes 22-23)
    bytes_0_21 = data[:21]
    results['16bit_22_23']['XOR'] = 0
    for i in range(0, len(bytes_0_21), 2):
        word = int.from_bytes(bytes_0_21[i:i+2], 'big') if i+1 < len(bytes_0_21) else bytes_0_21[i]
        results['16bit_22_23']['XOR'] ^= word
    results['16bit_22_23']['XOR'] &= 0xFFFF
    results['16bit_22_23']['Sum mod 65536'] = sum(bytes_0_21) % 65536
    results['16bit_22_23']['Simple sum'] = sum(bytes_0_21) & 0xFFFF
    crc16_ccitt = crcmod.predefined.mkCrcFun('crc-ccitt-false')
    results['16bit_22_23']['CRC-16-CCITT'] = crc16_ccitt(bytes_0_21)
    crc16_modbus = crcmod.mkCrcFun(0x18005, initCrc=0xFFFF, xorOut=0x0000)
    results['16bit_22_23']['CRC-16-Modbus'] = crc16_modbus(bytes_0_21)
    
    # 16-bit checksums (over bytes 0-20, compare to bytes 21-22)
    bytes_0_20 = data[:20]
    results['16bit_21_22']['XOR'] = 0
    for i in range(0, len(bytes_0_20), 2):
        word = int.from_bytes(bytes_0_20[i:i+2], 'big') if i+1 < len(bytes_0_20) else bytes_0_20[i]
        results['16bit_21_22']['XOR'] ^= word
    results['16bit_21_22']['XOR'] &= 0xFFFF
    results['16bit_21_22']['Sum mod 65536'] = sum(bytes_0_20) % 65536
    results['16bit_21_22']['Simple sum'] = sum(bytes_0_20) & 0xFFFF
    results['16bit_21_22']['CRC-16-CCITT'] = crc16_ccitt(bytes_0_20)
    results['16bit_21_22']['CRC-16-Modbus'] = crc16_modbus(bytes_0_20)
    
    return results

def parse_iot_packet(hex_string, endian='big'):
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
        
        # Counter (bytes 12-13)
        counter_be = int.from_bytes(data[12:14], 'big')
        counter_le = int.from_bytes(data[12:14], 'little')
        counter = counter_be if endian == 'big' else counter_le
        counter_hex = f"0x{counter_be:04x}" if endian == 'big' else f"0x{counter_le:04x}"
        
        # Other value (bytes 14-15, possibly RSSI/battery)
        other_be = int.from_bytes(data[14:16], 'big')
        other_le = int.from_bytes(data[14:16], 'little')
        other = other_be if endian == 'big' else other_le
        other_hex = f"0x{other_be:04x}" if endian == 'big' else f"0x{other_le:04x}"
        
        # Status bytes (byte 16 and 17 as alternatives)
        status_byte_16 = data[16]
        status_16 = "Pressed" if status_byte_16 == 0xFF else "Not Pressed"
        status_byte_17 = data[17]
        status_17 = "Pressed" if status_byte_17 == 0x80 else "Not Pressed"
        
        # Additional data/flags (bytes 18-21 if byte 17 is status, else 17-21)
        additional_data = data[18:22].hex(' ') if status_byte_17 == 0x80 else data[17:22].hex(' ')
        
        # Checksum: 8-bit (byte 23), 16-bit (bytes 22-23 or 21-22)
        actual_checksum_8bit = data[22]
        actual_checksum_16bit_22_23 = int.from_bytes(data[21:23], 'big')
        actual_checksum_16bit_21_22 = int.from_bytes(data[20:22], 'big')
        checksums = calculate_checksums(data)
        
        # Verify 8-bit checksum
        checksum_8bit_valid = "Not verified"
        for method, value in checksums['8bit'].items():
            if value == actual_checksum_8bit:
                checksum_8bit_valid = f"Verified with {method}"
                break
        
        # Verify 16-bit checksum (bytes 22-23)
        checksum_16bit_22_23_valid = "Not verified"
        for method, value in checksums['16bit_22_23'].items():
            if value == actual_checksum_16bit_22_23:
                checksum_16bit_22_23_valid = f"Verified with {method}"
                break
        
        # Verify 16-bit checksum (bytes 21-22)
        checksum_16bit_21_22_valid = "Not verified"
        for method, value in checksums['16bit_21_22'].items():
            if value == actual_checksum_16bit_21_22:
                checksum_16bit_21_22_valid = f"Verified with {method}"
                break
        
        # Output
        print("Parsed IoT Packet:")
        print(f"Header: {header.hex(' ')} (fixed identifier)")
        print(f"Sequence Number: 0x{seq:02x} ({seq})")
        print(f"Counter ({endian}-endian): {counter} ({counter_hex})")
        print(f"Counter ({'little' if endian == 'big' else 'big'}-endian): "
              f"{counter_le if endian == 'big' else counter_be} "
              f"(0x{counter_le:04x} if endian == 'big' else 0x{counter_be:04x})")
        print(f"Other Value ({endian}-endian): {other} ({other_hex})")
        print(f"Other Value ({'little' if endian == 'big' else 'big'}-endian): "
              f"{other_le if endian == 'big' else other_be} "
              f"(0x{other_le:04x} if endian == 'big' else 0x{other_be:04x})")
        print(f"Status Byte (byte 16): 0x{status_byte_16:02x} ({status_16})")
        print(f"Status Byte (byte 17, alternative): 0x{status_byte_17:02x} ({status_17})")
        print(f"Additional Data: {additional_data}")
        print(f"8-bit Checksum (byte 23): 0x{actual_checksum_8bit:02x} ({checksum_8bit_valid})")
        if checksum_8bit_valid == "Not verified":
            print("8-bit Checksum possibilities:")
            for method, value in checksums['8bit'].items():
                print(f"  {method}: 0x{value:02x}")
        print(f"16-bit Checksum (bytes 22-23): 0x{actual_checksum_16bit_22_23:04x} ({checksum_16bit_22_23_valid})")
        if checksum_16bit_22_23_valid == "Not verified":
            print("16-bit Checksum (22-23) possibilities:")
            for method, value in checksums['16bit_22_23'].items():
                print(f"  {method}: 0x{value:04x}")
        print(f"16-bit Checksum (bytes 21-22): 0x{actual_checksum_16bit_21_22:04x} ({checksum_16bit_21_22_valid})")
        if checksum_16bit_21_22_valid == "Not verified":
            print("16-bit Checksum (21-22) possibilities:")
            for method, value in checksums['16bit_21_22'].items():
                print(f"  {method}: 0x{value:04x}")
    
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

# Main: Get input from user
if __name__ == "__main__":
    # Install crcmod if needed: pip install crcmod
    endian = 'big'  # Default to big-endian per user expectation
    if len(sys.argv) > 2 and sys.argv[2] in ['big', 'little']:
        endian = sys.argv[2]
    elif len(sys.argv) == 1:
        print("Enter endianness (big/little, default: big): ", end='')
        user_endian = input().strip().lower()
        if user_endian in ['big', 'little']:
            endian = user_endian
    
    if len(sys.argv) > 1:
        hex_input = sys.argv[1]
    else:
        hex_input = input("Enter the 23-byte hex string: ").strip()
    parse_iot_packet(hex_input, endian)
