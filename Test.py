import binascii
import base64

def decode_udp_payload(hex_input):
    try:
        # Clean the input (remove spaces, colons, etc.)
        hex_input = hex_input.strip().replace(" ", "").replace(":", "")
        
        # Convert hex to bytes
        byte_data = bytes.fromhex(hex_input)

        print("=== Raw Bytes ===")
        print(byte_data)

        try:
            # Try UTF-8 decoding
            decoded_text = byte_data.decode('utf-8')
            print("\n=== UTF-8 Decoded Text ===")
            print(decoded_text)
        except UnicodeDecodeError:
            print("\n=== UTF-8 Decoding Failed ===")
            print("Not valid UTF-8 text. Showing byte values instead:")
            print(list(byte_data))

        # Optional: Base64 encoding (to inspect binary)
        b64 = base64.b64encode(byte_data).decode()
        print("\n=== Base64 Representation ===")
        print(b64)

    except ValueError as e:
        print("Invalid hex input:", e)

# Example usage
if __name__ == "__main__":
    # Example hex input (you can paste your own)
    hex_string = input("Enter UDP hex payload (e.g. 05a0ba44ba...): ")
    decode_udp_payload(hex_string)
