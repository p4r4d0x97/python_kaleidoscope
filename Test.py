import sys

def parse_iot_packet(hex_string, endian='big', packet_num=0, button_event="Unknown"):
    try:
        # Convert hex string to bytes
        data = bytes.fromhex(hex_string)
        if len(data) != 23:
            raise ValueError("Input must be a 23-byte hex string (46 characters).")
        
        # Expected header (bytes 0-10)
        expected_header = bytes.fromhex("05 a0 ba 44 ba 3d f2 0e 00 10 01")
        header = data[0:11]
        if header != expected_header:
            print(f"Warning (Packet {packet_num}): Header does not match expected value.")
        
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
        
        # Status bytes (byte 16, 17, 18, 19 as candidates)
        status_byte_16 = data[16]
        status_16 = "Pressed" if status_byte_16 == 0xFF else "Not Pressed"
        status_byte_17 = data[17]
        status_17 = "Pressed" if status_byte_17 == 0x80 else "Not Pressed"
        status_byte_18 = data[18]
        status_18 = "Pressed" if status_byte_18 == 0xFF else "Not Pressed"
        status_byte_19 = data[19]
        status_19 = "Pressed" if status_byte_19 == 0xFF else "Not Pressed"
        
        # Additional data (bytes 20-21 if byte 19 is status, else 19-21)
        additional_data = data[20:22].hex(' ') if status_byte_19 == 0xFF else data[19:22].hex(' ')
        
        # Packet sequence number (bytes 22-23, big-endian)
        packet_seq = int.from_bytes(data[21:23], 'big')
        
        # Check for overflow warning
        overflow_warning = ""
        if packet_seq >= 0xFF00:  # Close to 0xFFFF
            overflow_warning = f"Warning: Packet sequence near overflow (max 0xFFFF), next may wrap to 0x{(packet_seq + 0x100) & 0xFFFF:04x}"
        
        # Output
        print(f"\nParsed IoT Packet {packet_num}:")
        print(f"Button Event: {button_event}")
        print(f"Header: {header.hex(' ')} (fixed identifier)")
        print(f"Sequence Number (byte 11): 0x{seq:02x} ({seq})")
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
        print(f"Status Byte (byte 18, alternative): 0x{status_byte_18:02x} ({status_18})")
        print(f"Status Byte (byte 19, alternative): 0x{status_byte_19:02x} ({status_19})")
        print(f"Additional Data: {additional_data}")
        print(f"Packet Sequence Number (bytes 22-23): 0x{packet_seq:04x} ({packet_seq})")
        if overflow_warning:
            print(overflow_warning)
        
        return seq, packet_seq, status_byte_16, status_byte_17, status_byte_18, status_byte_19
    
    except ValueError as e:
        print(f"Error (Packet {packet_num}): {e}")
        return None, None, None, None, None, None
    except Exception as e:
        print(f"Unexpected error (Packet {packet_num}): {e}")
        return None, None, None, None, None, None

# Main: Get multiple packets from user
if __name__ == "__main__":
    endian = 'big'  # Default to big-endian
    if len(sys.argv) > 2 and sys.argv[2] in ['big', 'little']:
        endian = sys.argv[2]
    
    print("Enter packets (one per line, with optional button event, e.g., 'Unknown'). Enter blank line to finish:")
    packets = []
    while True:
        line = input().strip()
        if not line:
            break
        parts = line.split(' ', 1)
        hex_string = parts[0]
        button_event = parts[1] if len(parts) > 1 else "Unknown"
        packets.append((hex_string, button_event))
    
    if not packets:
        print("No packets provided.")
        sys.exit(1)
    
    # Parse packets and check sequence
    seq_numbers = []
    for i, (hex_string, button_event) in enumerate(packets, 1):
        seq, packet_seq, status_16, status_17, status_18, status_19 = parse_iot_packet(hex_string, endian, i, button_event)
        if seq is not None:
            seq_numbers.append((i, seq, packet_seq, status_16, status_17, status_18, status_19))
    
    # Analyze sequence numbers and status
    if seq_numbers:
        print("\nSequence and Status Analysis:")
        for packet_num, seq, packet_seq, status_16, status_17, status_18, status_19 in seq_numbers:
            print(f"Packet {packet_num}: Seq (byte 11)=0x{seq:02x}, Packet Seq (bytes 22-23)=0x{packet_seq:04x}, "
                  f"Status (16)=0x{status_16:02x} ({'P' if status_16 == 0xFF else 'NP'}), "
                  f"(17)=0x{status_17:02x} ({'P' if status_17 == 0x80 else 'NP'}), "
                  f"(18)=0x{status_18:02x} ({'P' if status_18 == 0xFF else 'NP'}), "
                  f"(19)=0x{status_19:02x} ({'P' if status_19 == 0xFF else 'NP'})")
        # Check packet sequence increment
        packet_seqs = [packet_seq for _, _, packet_seq, _, _, _, _ in seq_numbers]
        if len(packet_seqs) > 1:
            increments = [packet_seqs[i+1] - packet_seqs[i] for i in range(len(packet_seqs)-1)]
            print(f"Packet Sequence Increments: {increments}")
            # Check for overflow
            for i, inc in enumerate(increments):
                if packet_seqs[i] > packet_seqs[i+1]:
                    print(f"Overflow detected between Packet {i+1} (0x{packet_seqs[i]:04x}) and Packet {i+2} (0x{packet_seqs[i+1]:04x})")
