"""Replay captured NR-400 frames against the local server and compare replies with the real cloud's."""
import asyncio
import json
import sys
import urllib.request

HOST = "127.0.0.1"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 7000
HTTP = f"http://127.0.0.1:{sys.argv[2] if len(sys.argv) > 2 else 8080}"

# (boiler frame, the real cloud's reply) from captures/login_01.pcapng
REGISTER = ("f7030101047863a6e14a420402550010270000020b000004040110010700010104420015145a430082504d0022"
            "0000fe000019000000000000000000000400027c0a72035003e70f7c2d00002f8400003459000027000000"
            "000000000000000000000000f4b8")
REGISTER_REPLY = "f7010301047863a6e14a42046608000008010010270000ae73"
HEARTBEAT = "f7030101047863a6e14a4204010000363d"
REQ_CONFIG = "f7020301047863a6e14a4204cd0000c7cc"
CONFIG = ("f7030101047863a6e14a420405200007000101000b10010202031450033c8201010102033c7801030202010101"
          "0201bcd4")
CONFIG_REPLY = "f7010301047863a6e14a420469080000080100102700006eb3"
QUERY_STATUS = "f7020301047863a6e14a4204cf0100006685"
STATUS = ("f7030101047863a6e14a4204071d0001ff0006010000000601422e525a010a000000030000000000000000"
          "01e79e")
STATUS_REPLY = "f7010301047863a6e14a42046b01000135ba"
SET_41 = "f7020301047863a6e14a4204ce02000652adc0"
AWAY = "f7020301047863a6e14a4204ce010004729d"


async def read_frame(reader):
    head = await asyncio.wait_for(reader.readexactly(15), 3)
    length = int.from_bytes(head[13:15], "little")
    return (head + await reader.readexactly(length + 2)).hex()


def http(path):
    try:
        with urllib.request.urlopen(HTTP + path, timeout=3) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


async def main():
    failures = []

    def check(name, got, want):
        ok = got == want
        print(f"[{'OK' if ok else 'FAIL'}] {name}" + ("" if ok else f"\n   got  {got}\n   want {want}"))
        if not ok:
            failures.append(name)

    reader, writer = await asyncio.open_connection(HOST, PORT)
    writer.write(bytes.fromhex(REGISTER))
    check("register reply == cloud", await read_frame(reader), REGISTER_REPLY)

    writer.write(bytes.fromhex(HEARTBEAT))
    time_reply = await read_frame(reader)
    check("heartbeat reply is time frame", time_reply[24:30], "650600")
    check("config request after first heartbeat", await read_frame(reader), REQ_CONFIG)

    writer.write(bytes.fromhex(CONFIG))
    check("config reply == cloud", await read_frame(reader), CONFIG_REPLY)
    check("status query after config", await read_frame(reader), QUERY_STATUS)

    writer.write(bytes.fromhex(STATUS))
    check("status reply == cloud", await read_frame(reader), STATUS_REPLY)
    await writer.drain()
    await asyncio.sleep(0.2)

    st = await asyncio.to_thread(http, "/status")
    print("   /status ->", json.dumps(st["status"] | {"raw": "..."}, ensure_ascii=False))
    check("/status set_temp", st["status"]["set_temp"], 41.0)
    check("/status room_temp", st["status"]["room_temp"], 23.0)

    print("   /set?temp=41 ->", await asyncio.to_thread(http, "/set?temp=41"))
    check("/set?temp=41 frame == cloud command", await read_frame(reader), SET_41)
    print("   /mode?name=away ->", await asyncio.to_thread(http, "/mode?name=away"))
    check("/mode?name=away frame == cloud command", await read_frame(reader), AWAY)
    check("/set?temp=80 rejected", "error" in await asyncio.to_thread(http, "/set?temp=80"), True)

    writer.close()
    print("\nALL PASSED" if not failures else f"\nFAILED: {failures}")
    sys.exit(1 if failures else 0)


asyncio.run(main())
