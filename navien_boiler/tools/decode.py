"""Decode NR-400 <-> cloud (TCP 7000) frames from a pcap via tshark.

Frame layout (observed):
  f7 | kind | dir | 01 | MAC(6) | 42 04 | cmd | len(u16 LE) | payload(len) | CRC-16/BUYPASS (BE)
"""
import subprocess
import sys

TSHARK = r"C:\Program Files\Wireshark\tshark.exe"

CMD_NAMES = {
    0x01: "heartbeat",
    0x02: "register",
    0x05: "config",
    0x66: "reg-ack",
    0x69: "cfg-ack",
    0xCD: "req-cfg",
    0x07: "status",
    0x65: "time",
    0x6B: "ack",
    0xCE: "control",
    0xCF: "query",
}
MODE_NAMES = {0x01: "off", 0x02: "on", 0x04: "away", 0x06: "ondol"}


def crc16_buypass(data):
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x8005) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def split_frames(stream):
    """A TCP segment may carry several frames; split by the length field."""
    i = 0
    while i + 15 <= len(stream):
        if stream[i] != 0xF7:
            yield None, stream[i:]
            return
        length = int.from_bytes(stream[i + 13 : i + 15], "little")
        end = i + 15 + length + 2
        yield stream[i:end], None
        i = end


def describe(cmd, payload):
    if cmd == 0xCE and payload:
        mode = MODE_NAMES.get(payload[0], f"0x{payload[0]:02x}")
        if len(payload) > 1:
            return f"set mode={mode} temp={payload[1] / 2:.1f}C"
        return f"set mode={mode}"
    if cmd == 0xCF and payload:
        return {0x00: "request status", 0x0E: "request schedule"}.get(payload[0], f"0x{payload[0]:02x}")
    if cmd == 0x07 and len(payload) == 29:
        mode = MODE_NAMES.get(payload[8], f"0x{payload[8]:02x}")
        return (
            f"mode={mode} room={payload[11] / 2:.1f}C set={payload[12] / 2:.1f}C "
            f"b10={payload[10] / 2:.1f} b13={payload[13] / 2:.1f}"
        )
    if cmd == 0x65 and len(payload) == 6:
        y, mo, d, wd, h, mi = payload  # weekday: Sun=1 .. Sat=7
        day = "Sun Mon Tue Wed Thu Fri Sat".split()[wd - 1] if 1 <= wd <= 7 else f"wd{wd}"
        return f"20{y:02d}-{mo:02d}-{d:02d} {day} {h:02d}:{mi:02d}"
    return ""


def main(pcap):
    out = subprocess.run(
        [TSHARK, "-r", pcap, "-Y", "tcp.len>0 && tcp.port==7000", "-T", "fields",
         "-e", "frame.time_relative", "-e", "tcp.payload", "-E", "separator=|"],
        capture_output=True, text=True, check=True,
    ).stdout
    bad = 0
    for line in out.splitlines():
        t, hexdata = line.split("|")
        for frame, junk in split_frames(bytes.fromhex(hexdata)):
            if junk is not None:
                print(f"{float(t):8.2f} ???? UNPARSED {junk.hex()}")
                bad += 1
                continue
            # header byte 1: 0x03 = boiler report, 0x01/0x02 = server reply/command
            direction = "B->S" if frame[1] == 0x03 else "S->B"
            ok = crc16_buypass(frame[:-2]) == int.from_bytes(frame[-2:], "big")
            bad += not ok
            cmd, payload = frame[12], frame[15:-2]
            name = CMD_NAMES.get(cmd, f"0x{cmd:02x}")
            print(f"{float(t):8.2f} {direction} hdr={frame[1:4].hex()} {name:9} "
                  f"len={len(payload):3} crc={'ok' if ok else 'BAD'} "
                  f"{describe(cmd, payload)} | {payload[:32].hex()}")
    print(f"\nframes with problems: {bad}")


if __name__ == "__main__":
    main(sys.argv[1])
