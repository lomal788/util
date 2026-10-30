"""Send raw A/AAAA queries to a DNS server and print the answers (no nslookup quirks)."""
import random
import socket
import struct
import sys


def query(server, port, name, qtype):
    tid = random.randint(0, 0xFFFF)
    q = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    q += b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\x00"
    q += struct.pack(">HH", qtype, 1)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    try:
        s.sendto(q, (server, port))
        resp = s.recv(2048)
    except socket.timeout:
        return "TIMEOUT"
    rcode = resp[3] & 0x0F
    ancount = struct.unpack(">H", resp[6:8])[0]
    i = len(q)
    answers = []
    for _ in range(ancount):
        i = i + 2 if resp[i] & 0xC0 == 0xC0 else resp.index(b"\x00", i) + 1
        rtype, _, _, rdlen = struct.unpack(">HHIH", resp[i:i + 10])
        rdata = resp[i + 10:i + 10 + rdlen]
        if rtype == 1:
            answers.append(socket.inet_ntoa(rdata))
        elif rtype == 28:
            answers.append(socket.inet_ntop(socket.AF_INET6, rdata))
        else:
            answers.append(f"type{rtype}")
        i += 10 + rdlen
    return f"rcode={rcode} answers={answers}"


if __name__ == "__main__":
    server, port = sys.argv[1], int(sys.argv[2])
    for name in sys.argv[3:]:
        for qtype, label in ((1, "A"), (28, "AAAA")):
            print(f"{name:32} {label:4} {query(server, port, name, qtype)}")
