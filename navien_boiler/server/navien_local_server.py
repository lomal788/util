"""Local stand-in for the Navien Smart-Tok cloud (krst2.naviensmartcontrol.com:7000).

Point the boiler's DNS lookup of krst2.naviensmartcontrol.com at this machine and
the NR-400 WiFi module connects here instead of the cloud.

  TCP 7000  boiler protocol (plaintext, CRC-16/BUYPASS)
  HTTP 8080 control API
      GET /status                     latest decoded status (JSON)
      GET /set?temp=40                ondol mode at 40.0 C (0.5 C steps)
      GET /mode?name=off|on|away      power / away
      GET /refresh                    ask the boiler for a fresh status

Frame: f7 | kind | dir | 01 | MAC(6) | 42 04 | cmd | len(u16 LE) | payload | CRC16 (BE)
"""
import argparse
import asyncio
import json
import logging
import time
from datetime import datetime
from urllib.parse import parse_qs, urlsplit

log = logging.getLogger("navien")

# Header bytes 1..3 seen on the wire.
HDR_BOILER = bytes([0x03, 0x01, 0x01])   # boiler -> server
HDR_REPLY = bytes([0x01, 0x03, 0x01])    # server reply to a boiler frame
HDR_COMMAND = bytes([0x02, 0x03, 0x01])  # server-initiated command
ADDR_TAIL = bytes([0x42, 0x04])

CMD_HEARTBEAT, CMD_REGISTER, CMD_CONFIG, CMD_STATUS = 0x01, 0x02, 0x05, 0x07
CMD_REQ_CONFIG, CMD_CONTROL, CMD_QUERY = 0xCD, 0xCE, 0xCF
REPLY_OFFSET = 0x64  # reply cmd = boiler cmd + 0x64

MODES = {"off": 0x01, "on": 0x02, "away": 0x04, "ondol": 0x06}
MODE_NAMES = {v: k for k, v in MODES.items()}
TEMP_MIN, TEMP_MAX = 10.0, 45.0  # 45 C is the upper bound the boiler reports


def crc16_buypass(data):
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x8005) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def build_frame(header, mac, cmd, payload=b""):
    body = (bytes([0xF7]) + header + mac + ADDR_TAIL + bytes([cmd])
            + len(payload).to_bytes(2, "little") + payload)
    return body + crc16_buypass(body).to_bytes(2, "big")


def time_payload(now=None):
    """yy mm dd weekday(Sun=1..Sat=7) hh mm, local time."""
    now = now or datetime.now()
    weekday = (now.isoweekday() % 7) + 1
    return bytes([now.year % 100, now.month, now.day, weekday, now.hour, now.minute])


def decode_status(payload):
    if len(payload) != 29:
        return {"raw": payload.hex()}
    return {
        "mode": MODE_NAMES.get(payload[8], f"0x{payload[8]:02x}"),
        "last_heating_mode": MODE_NAMES.get(payload[3], f"0x{payload[3]:02x}"),
        "room_temp": payload[11] / 2,
        "set_temp": payload[12] / 2,
        "unknown_b10": payload[10] / 2,
        "max_temp": payload[13] / 2,
        "raw": payload.hex(),
    }


class Boiler:
    """One connected NR-400 session."""

    def __init__(self, reader, writer):
        self.reader, self.writer = reader, writer
        self.mac = None
        self.register_tag = b"\x10\x27\x00\x00"
        self.status = None
        self.status_time = None
        self.schedule = None
        self.config = None
        self.sent_config_request = False

    async def send(self, header, cmd, payload=b""):
        frame = build_frame(header, self.mac, cmd, payload)
        log.info("S->B %s", frame.hex())
        self.writer.write(frame)
        await self.writer.drain()

    async def command(self, cmd, payload=b""):
        await self.send(HDR_COMMAND, cmd, payload)

    async def handle(self, cmd, payload):
        reply = cmd + REPLY_OFFSET
        if cmd == CMD_REGISTER:
            self.register_tag = payload[:4]
            log.info("register: %s", payload.hex())
            await self.send(HDR_REPLY, reply, b"\x00\x08\x01\x00" + self.register_tag)
        elif cmd == CMD_HEARTBEAT:
            await self.send(HDR_REPLY, reply, time_payload())
            if not self.sent_config_request:
                self.sent_config_request = True
                await self.command(CMD_REQ_CONFIG)
        elif cmd == CMD_CONFIG:
            self.config = payload
            log.info("config: %s", payload.hex())
            await self.send(HDR_REPLY, reply, b"\x00\x08\x01\x00" + self.register_tag)
            await self.command(CMD_QUERY, b"\x00")
        elif cmd == CMD_STATUS:
            if payload[:1] == b"\x0e":
                self.schedule = payload
            else:
                self.status = decode_status(payload)
                self.status_time = time.time()
                log.info("status: %s", {k: v for k, v in self.status.items() if k != "raw"})
            await self.send(HDR_REPLY, reply, payload[:1])
        else:
            log.warning("unhandled cmd 0x%02x payload %s", cmd, payload.hex())

    async def run(self):
        buf = b""
        while True:
            chunk = await self.reader.read(4096)
            if not chunk:
                return
            buf += chunk
            while len(buf) >= 17:
                if buf[0] != 0xF7:
                    log.warning("resync, dropping %s", buf[:1].hex())
                    buf = buf[1:]
                    continue
                length = int.from_bytes(buf[13:15], "little")
                end = 15 + length + 2
                if len(buf) < end:
                    break
                frame, buf = buf[:end], buf[end:]
                log.info("B->S %s", frame.hex())
                if crc16_buypass(frame[:-2]) != int.from_bytes(frame[-2:], "big"):
                    log.warning("bad CRC, ignored")
                    continue
                self.mac = frame[4:10]
                await self.handle(frame[12], frame[15:-2])


class Hub:
    def __init__(self):
        self.boiler = None

    async def on_boiler(self, reader, writer):
        peer = writer.get_extra_info("peername")
        log.info("boiler connected from %s", peer)
        boiler = Boiler(reader, writer)
        self.boiler = boiler
        try:
            await boiler.run()
        except (ConnectionError, asyncio.IncompleteReadError) as exc:
            log.info("boiler connection error: %s", exc)
        finally:
            log.info("boiler %s disconnected", peer)
            if self.boiler is boiler:
                self.boiler = None
            writer.close()

    async def api(self, path, query):
        b = self.boiler
        if path == "/status":
            if not b:
                return 503, {"connected": False}
            return 200, {
                "connected": True,
                "mac": b.mac.hex(":") if b.mac else None,
                "status": b.status,
                "status_age_s": round(time.time() - b.status_time, 1) if b.status_time else None,
            }
        if not b or not b.mac:
            return 503, {"error": "boiler not connected"}
        if path == "/set":
            temp = float(query.get("temp", ["nan"])[0])
            if not TEMP_MIN <= temp <= TEMP_MAX:
                return 400, {"error": f"temp must be {TEMP_MIN}..{TEMP_MAX}"}
            await b.command(CMD_CONTROL, bytes([MODES["ondol"], round(temp * 2)]))
            return 200, {"sent": f"ondol {round(temp * 2) / 2}C"}
        if path == "/mode":
            name = query.get("name", [""])[0]
            if name not in ("off", "on", "away"):
                return 400, {"error": "name must be off|on|away"}
            await b.command(CMD_CONTROL, bytes([MODES[name]]))
            return 200, {"sent": name}
        if path == "/refresh":
            await b.command(CMD_QUERY, b"\x00")
            return 200, {"sent": "query"}
        return 404, {"error": "unknown path"}

    async def on_http(self, reader, writer):
        try:
            request_line = (await reader.readline()).decode("latin-1").split()
            while (await reader.readline()) not in (b"\r\n", b"\n", b""):
                pass
            if len(request_line) < 2:
                return
            url = urlsplit(request_line[1])
            try:
                code, body = await self.api(url.path, parse_qs(url.query))
            except ValueError as exc:
                code, body = 400, {"error": str(exc)}
            data = json.dumps(body, ensure_ascii=False).encode()
            writer.write(
                f"HTTP/1.1 {code} X\r\nContent-Type: application/json; charset=utf-8\r\n"
                f"Content-Length: {len(data)}\r\nConnection: close\r\n\r\n".encode() + data
            )
            await writer.drain()
        finally:
            writer.close()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=7000)
    ap.add_argument("--http-bind", default="127.0.0.1")
    ap.add_argument("--http-port", type=int, default=8080)
    ap.add_argument("--log", default="navien_server.log")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(args.log, encoding="utf-8")],
    )
    hub = Hub()
    boiler_srv = await asyncio.start_server(hub.on_boiler, args.bind, args.port)
    http_srv = await asyncio.start_server(hub.on_http, args.http_bind, args.http_port)
    log.info("boiler port %s:%d, http %s:%d", args.bind, args.port, args.http_bind, args.http_port)
    async with boiler_srv, http_srv:
        await asyncio.gather(boiler_srv.serve_forever(), http_srv.serve_forever())


if __name__ == "__main__":
    asyncio.run(main())
