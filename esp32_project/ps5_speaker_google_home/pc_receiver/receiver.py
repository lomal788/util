"""ESP32-S3 가 보내는 PS5 소리(48 kHz 스테레오 16 bit)를 받아 재생한다.

    pip install -r requirements.txt
    python receiver.py --serial COM11     # 유선 (보드의 UART 단자)
    python receiver.py                    # Wi-Fi, 같은 공유기 안에서 S3 를 자동으로 찾음
    python receiver.py --ip 192.168.0.28  # Wi-Fi, 주소 지정
    python receiver.py --list             # 출력 장치 목록
"""

import argparse
import math
import socket
import struct
import threading
import time

import sounddevice as sd

RATE = 48000
CHANNELS = 2
FRAME = 4
PORT = 4010
MAGIC = b"\xa5\x5a"
HELLO = b"PS5SPK_HELLO"
BEACON = b"PS5SPK_BEACON"
SERIAL_HEADER = 10
SERIAL_MAX_PAYLOAD = 4096


def ms_to_bytes(ms):
    return int(RATE * ms / 1000) * FRAME


def bytes_to_ms(n):
    return n / FRAME / RATE * 1000


class Player:
    def __init__(self, buffer_ms, gain_db=0.0):
        self.gain = 10 ** (gain_db / 20)
        margin_ms = max(5, buffer_ms / 3)
        self.lock = threading.Lock()
        self.buf = bytearray()
        self.target = ms_to_bytes(buffer_ms)
        self.low = ms_to_bytes(buffer_ms - margin_ms)
        self.high = ms_to_bytes(buffer_ms + margin_ms)
        self.limit = ms_to_bytes(buffer_ms + 100)
        self.filling = True
        self.underruns = 0
        self.resyncs = 0
        self.min_level = None
        self.peak = 0

    def take_peak_text(self):
        peak, self.peak = self.peak, 0
        if peak == 0:
            return "silent"
        text = f"{20 * math.log10(peak / 32768):5.1f} dBFS"
        return text + " CLIP" if peak >= 32767 else text

    def push(self, pcm):
        if self.gain != 1.0:
            import numpy as np

            samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) * self.gain
            pcm = np.clip(samples, -32768, 32767).astype("<i2").tobytes()
        samples = memoryview(pcm).cast("h")
        peak = max(max(samples), -min(samples))
        if peak > self.peak:
            self.peak = peak
        with self.lock:
            self.buf += pcm

    def take_min_level_ms(self):
        with self.lock:
            level = self.min_level
            self.min_level = None
        return bytes_to_ms(level) if level is not None else 0.0

    def callback(self, outdata, frames, time_info, status):
        need = frames * FRAME
        with self.lock:
            buf = self.buf
            if self.filling:
                if len(buf) < self.target:
                    outdata[:] = b"\x00" * need
                    return
                self.filling = False

            if len(buf) > self.limit:
                # 크게 밀렸으면 목표치만 남기고 오래된 것을 버린다.
                drop = (len(buf) - self.target) // FRAME * FRAME
                del buf[:drop]
                self.resyncs += 1

            if self.min_level is None or len(buf) < self.min_level:
                self.min_level = len(buf)

            if len(buf) < need:
                got = len(buf)
                outdata[:got] = bytes(buf)
                outdata[got:] = b"\x00" * (need - got)
                buf.clear()
                self.filling = True
                self.underruns += 1
                return

            # PS5 와 PC 의 클럭이 조금 달라 버퍼가 서서히 차거나 빈다.
            # 콜백마다 한 프레임씩 버리거나 되풀이해서 목표치 근처로 되돌린다.
            if len(buf) > self.high and len(buf) >= need + FRAME:
                del buf[:FRAME]
                outdata[:] = bytes(buf[:need])
                del buf[:need]
            elif len(buf) < self.low and need > FRAME:
                take = need - FRAME
                chunk = bytes(buf[:take])
                del buf[:take]
                outdata[:] = chunk + chunk[-FRAME:]
            else:
                outdata[:] = bytes(buf[:need])
                del buf[:need]


class Stats:
    def __init__(self, player):
        self.player = player
        self.expect = None
        self.lost = 0
        self.corrupt = 0
        self.packets = 0
        self.last = time.monotonic()

    def packet(self, seq):
        if self.expect is not None and seq != self.expect:
            self.lost += (seq - self.expect) & 0xFFFF
        self.expect = (seq + 1) & 0xFFFF
        self.packets += 1

    def tick(self):
        now = time.monotonic()
        if now - self.last < 5.0:
            return
        self.last = now
        if self.packets:
            p = self.player
            print(
                f"peak {p.take_peak_text()} | buffer min {p.take_min_level_ms():5.1f} ms | lost {self.lost} | "
                f"corrupt {self.corrupt} | underrun {p.underruns} | resync {p.resyncs}"
            )
        self.packets = 0


def pick_output_device(arg):
    if arg is not None:
        return int(arg) if arg.isdigit() else arg
    # Windows 기본값인 MME 는 지연이 커서 WASAPI 의 기본 출력 장치를 쓴다.
    for api in sd.query_hostapis():
        if "WASAPI" in api["name"] and api["default_output_device"] >= 0:
            return api["default_output_device"]
    return None


def open_stream(player, device, block_ms):
    kwargs = dict(
        samplerate=RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=int(RATE * block_ms / 1000),
        latency="low",
        device=device,
        callback=player.callback,
    )
    # WASAPI 독점 모드는 쓰지 않는다. 이 PC(Realtek)에서 파이썬 콜백으로 열면 콜백이 몇 번 만에 멈춰
    # 삐 소리만 나고, Windows 오디오 서비스까지 죽었다 (2026-11-21 시험).
    # WASAPI 공유 모드는 장치 설정이 48 kHz 가 아니면 열리지 않는다. 변환을 맡긴다.
    try:
        return sd.RawOutputStream(extra_settings=sd.WasapiSettings(auto_convert=True), **kwargs)
    except Exception:
        return sd.RawOutputStream(**kwargs)


def run_udp(args, player, stats):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", PORT))
    sock.settimeout(0.5)

    server = (args.ip, PORT) if args.ip else None
    if server is None:
        print("searching for S3 ...")

    last_hello = 0.0
    while True:
        now = time.monotonic()
        if server and now - last_hello >= 1.0:
            sock.sendto(HELLO, server)
            last_hello = now
        stats.tick()

        try:
            data, addr = sock.recvfrom(2048)
        except socket.timeout:
            continue
        except ConnectionResetError:
            # Windows 는 상대 포트가 닫혀 있으면 UDP 수신에서 이 예외를 던진다.
            continue

        if data == BEACON:
            if server is None or server[0] != addr[0]:
                server = (addr[0], PORT)
                last_hello = 0.0
                print("S3 found:", addr[0])
            continue

        if len(data) <= 4 or data[:2] != MAGIC:
            continue
        if server is None or addr[0] != server[0]:
            continue

        stats.packet(struct.unpack_from("<H", data, 2)[0])
        pcm = data[4:]
        player.push(pcm[: len(pcm) // FRAME * FRAME])


class LogLines:
    """오디오 패킷 사이에 섞여 오는 S3 의 로그 글자를 줄 단위로 보여 준다."""

    def __init__(self):
        self.line = bytearray()

    def feed(self, data):
        for b in data:
            if b == 0x0A:
                text = self.line.decode("ascii", "ignore").strip()
                if len(text) >= 3:
                    print("[S3]", text)
                self.line.clear()
            elif 0x20 <= b < 0x7F and len(self.line) < 200:
                self.line.append(b)
            elif b != 0x0D:
                # 부트 ROM 이 다른 속도로 내보낸 글자는 깨져 보이므로 버린다.
                self.line.clear()


def run_serial(args, player, stats):
    import serial

    ser = serial.Serial()
    ser.port = args.serial
    ser.baudrate = args.baud
    ser.timeout = 0.2
    # DTR/RTS 가 움직이면 보드의 자동 리셋 회로가 S3 를 재시작시킨다.
    ser.dtr = False
    ser.rts = False
    ser.open()
    # 초당 192 KB 가 들어온다. Windows 기본 수신 버퍼(4 KB)는 약 20 ms 분량이라
    # 읽는 쪽이 잠깐만 밀려도 넘쳐서 바이트가 사라진다.
    if hasattr(ser, "set_buffer_size"):
        ser.set_buffer_size(rx_size=1 << 20)
    print(f"serial: {args.serial} @ {args.baud}")

    logs = LogLines()
    buf = bytearray()
    while True:
        stats.tick()
        chunk = ser.read(ser.in_waiting or 1)
        if not chunk:
            continue
        buf += chunk

        while True:
            i = buf.find(MAGIC)
            if i < 0:
                # 마지막 바이트는 다음에 올 패킷 머리의 첫 바이트일 수 있다.
                keep = 1 if buf.endswith(MAGIC[:1]) else 0
                logs.feed(buf[: len(buf) - keep])
                del buf[: len(buf) - keep]
                break
            if i > 0:
                logs.feed(buf[:i])
                del buf[:i]
            if len(buf) < SERIAL_HEADER:
                break
            seq, length, inverse, checksum = struct.unpack_from("<HHHH", buf, 2)
            if length ^ inverse != 0xFFFF or length == 0 or length > SERIAL_MAX_PAYLOAD or length % FRAME:
                del buf[:1]
                continue
            if len(buf) < SERIAL_HEADER + length:
                break
            pcm = bytes(buf[SERIAL_HEADER : SERIAL_HEADER + length])
            if sum(pcm) & 0xFFFF != checksum:
                # 바이트가 빠졌으면 패킷 경계도 틀렸을 수 있으니 머리만 넘기고 다시 찾는다.
                stats.corrupt += 1
                del buf[:2]
                continue
            del buf[: SERIAL_HEADER + length]
            player.push(pcm)
            stats.packet(seq)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", metavar="PORT", help="유선으로 받을 COM 포트 (예: COM11). 생략하면 Wi-Fi")
    ap.add_argument("--baud", type=int, default=3000000, help="유선 속도. config.h 의 UART_BAUD 와 같아야 함")
    ap.add_argument("--ip", help="Wi-Fi 일 때 S3 주소. 생략하면 자동으로 찾음")
    ap.add_argument("--buffer-ms", type=int, help="지터 버퍼 목표 길이 (기본: 유선 20, Wi-Fi 40)")
    ap.add_argument("--block-ms", type=int, help="오디오 콜백 길이 (기본: 유선 5, Wi-Fi 10)")
    ap.add_argument("--gain-db", type=float, default=0.0, help="받은 소리를 키우는 양 (dB). 0 이면 원본 그대로, 넘치는 값은 잘림")
    ap.add_argument("--device", help="출력 장치 번호나 이름")
    ap.add_argument("--list", action="store_true", help="출력 장치 목록을 보여 주고 끝냄")
    args = ap.parse_args()

    if args.list:
        print(sd.query_devices())
        return

    wired = args.serial is not None
    buffer_ms = args.buffer_ms or (20 if wired else 40)
    block_ms = args.block_ms or (5 if wired else 10)

    player = Player(buffer_ms, args.gain_db)
    stats = Stats(player)
    stream = open_stream(player, pick_output_device(args.device), block_ms)
    print("output:", sd.query_devices(stream.device)["name"], f"({stream.latency * 1000:.1f} ms)")
    print(f"buffer {buffer_ms} ms, block {block_ms} ms, gain {args.gain_db:+.1f} dB")

    with stream:
        if wired:
            run_serial(args, player, stats)
        else:
            run_udp(args, player, stats)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
