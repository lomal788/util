"""Find the checksum used by the NR-400 <-> cloud protocol (port 7000)."""
import itertools
import sys

PACKETS = [
    "f7020301047863a6e14a4204ce02000652adc0",
    "f7030101047863a6e14a4204071d0001ff0006010000000601422e525a010a00000003000000000000000001e79e",
    "f7010301047863a6e14a42046b01000135ba",
    "f7020301047863a6e14a4204ce010004729d",
    "f7030101047863a6e14a4204010000363d",
    "f7010301047863a6e14a42046506001a0a1e060c396cbc",
    "f7020301047863a6e14a4204cf0100006685",
    "f7020301047863a6e14a4204cf01000ee6a2",
    "f7010301047863a6e14a42046b01000e3598",
]


def crc16(data, poly, init, refin, refout, xorout):
    crc = init
    for b in data:
        if refin:
            b = int(f"{b:08b}"[::-1], 2)
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ poly) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    if refout:
        crc = int(f"{crc:016b}"[::-1], 2)
    return crc ^ xorout


def main():
    pkts = [bytes.fromhex(p) for p in PACKETS]
    polys = [0x1021, 0x8005, 0x3D65, 0x0589, 0x8BB7, 0xA097, 0xC867]
    inits = [0x0000, 0xFFFF, 0x1D0F, 0x89EC]
    hits = []
    for poly, init, refin, refout, xorout, start in itertools.product(
        polys, inits, (False, True), (False, True), (0x0000, 0xFFFF), range(0, 4)
    ):
        for endian in ("big", "little"):
            if all(
                crc16(p[start:-2], poly, init, refin, refout, xorout).to_bytes(2, endian) == p[-2:]
                for p in pkts
            ):
                hits.append((hex(poly), hex(init), refin, refout, hex(xorout), start, endian))
    for h in hits:
        print("CRC16 hit: poly=%s init=%s refin=%s refout=%s xorout=%s start=%d %s" % h)
    if not hits:
        print("no CRC16 match")
    sys.exit(0)


if __name__ == "__main__":
    main()
