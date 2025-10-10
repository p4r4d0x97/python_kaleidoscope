#!/usr/bin/env python3
# analyze_packets.py
import binascii, struct, datetime

# --- paste your packets here (one per line) ---
hex_packets = [
    "05a0ba44ba3df20e001001076b290d618000800000049d",
    "05a0ba44ba3df20e0010010c7ed03d00ff00000000961e",
]

def to_bytes(h): return bytes.fromhex(h.strip().replace(" ","").replace(":",""))

packets = [to_bytes(h) for h in hex_packets]
print("Packets loaded:", len(packets), "lengths:", [len(p) for p in packets])
print()

# 1) constants / variability
maxlen = max(len(p) for p in packets)
print("Index  Hex (packet values)   UniqueCount")
for i in range(maxlen):
    vals = []
    for p in packets:
        vals.append(p[i] if i < len(p) else None)
    uniq = sorted(set(vals))
    print(f"{i:02d}   ", " ".join((f"{v:02x}" if v is not None else "--") for v in vals), "    ", len([v for v in uniq if v is not None]))
print()

# 2) check 4-byte timestamp candidates (LE and BE)
def plausible_unix(ts):
    return 946684800 <= ts <= 2082758400   # 2000..2035

print("4-byte timestamp scan (offset, endian, values -> iso):")
for off in range(0, maxlen-3):
    vals_le = []
    vals_be = []
    ok_le = True
    ok_be = True
    for p in packets:
        if off+4 > len(p):
            ok_le = ok_be = False
            break
        v_le = int.from_bytes(p[off:off+4], 'little')
        v_be = int.from_bytes(p[off:off+4], 'big')
        vals_le.append(v_le)
        vals_be.append(v_be)
        if not plausible_unix(v_le):
            ok_le = False
        if not plausible_unix(v_be):
            ok_be = False
    if ok_le:
        print("OFF", off, "LE ->", [ (v, datetime.datetime.utcfromtimestamp(v).isoformat()+"Z") for v in vals_le ])
    if ok_be:
        print("OFF", off, "BE ->", [ (v, datetime.datetime.utcfromtimestamp(v).isoformat()+"Z") for v in vals_be ])
print()

# 3) checksum/CRC tests for tail lengths 1..4 and common CRCs
import binascii
def crc32(data): return binascii.crc32(data) & 0xffffffff

# simple CRC presets: check CRC-32, CRC-16 (binascii can't do CRC16; use basic func below)
def crc16_ccitt(data, poly=0x1021, init=0xffff):
    reg = init
    for b in data:
        reg ^= (b << 8)
        for _ in range(8):
            if reg & 0x8000:
                reg = ((reg << 1) ^ poly) & 0xffff
            else:
                reg = (reg << 1) & 0xffff
    return reg & 0xffff

print("Checksum tests (compare computed checksum of prefix to tail bytes):")
for tail_len in (1,2,3,4):
    print(" tail_len =", tail_len)
    for pos in range(0, maxlen-tail_len+1):
        all_match_crc32 = True if tail_len==4 else False
        all_match_crc16 = True if tail_len==2 else False
        all_match_simple_sum = True
        for p in packets:
            if pos+tail_len > len(p):
                all_match_crc32 = all_match_crc16 = all_match_simple_sum = False
                break
            prefix = p[:pos]
            tail = p[pos:pos+tail_len]
            # CRC32 case
            if tail_len==4:
                val = crc32(prefix)
                if val != int.from_bytes(tail,'big'):
                    all_match_crc32 = False
            # CRC16 test
            if tail_len==2:
                val2 = crc16_ccitt(prefix)
                if val2 != int.from_bytes(tail,'big'):
                    all_match_crc16 = False
            # simple sum mod 2^taillen*8
            s = sum(prefix) & ((1<<(tail_len*8))-1)
            if s != int.from_bytes(tail,'big'):
                all_match_simple_sum = False
        if tail_len==4 and all_match_crc32:
            print(f"  pos {pos}: ALL packets match CRC32 -> tail bytes match crc32(prefix)")
        if tail_len==2 and all_match_crc16:
            print(f"  pos {pos}: ALL packets match CRC16-CCITT -> tail bytes match crc16(prefix)")
        if all_match_simple_sum:
            print(f"  pos {pos}: ALL packets match simple byte-sum mod 2^{tail_len*8}")

print()
print("Done. If nothing matched, try adding more packets (3..10) for higher confidence.")
