"""Set the NR-400 WiFi without the Smart-Tok app.

1. Put the thermostat in WiFi setup (AP) mode: with the boiler OFF, hold the [+] button
   for 3 seconds. It opens an open network "NR40-xxxx".
2. Connect this PC to that network (the boiler is 192.168.43.1).
3. python tools/provision.py                      # pick a number, type the password
   python tools/provision.py --list               # only show what the boiler sees
   python tools/provision.py --ssid jerry2        # non-interactive

Protocol (captured from the app): POST http://192.168.43.1/process_data.json with
{"command_id": "kdoneNNN", "command_type": ..., "request_value": "get"|"set"[, "data": ...]}.
The module answers one request per connection.
"""
import argparse
import getpass
import http.client
import json
import sys
import time

HOST = "192.168.43.1"
OPEN_SECURITY = {"OPEN", "NONE", ""}
SETUP_GUIDE = """\
[준비]
  1. 조절기(NR-400)에서 보일러를 '끈' 상태로 만듭니다.
  2. 그 상태에서 [+] 버튼을 3초간 누르면 WiFi 설정 모드가 켜집니다.
  3. PC WiFi 목록에 생긴 'NR40-xxxx'(암호 없음)에 연결합니다.
"""


def call(command_id, command_type, request_value, data=None, timeout=10):
    body = {"command_id": command_id, "command_type": command_type}
    if data is not None:
        body["data"] = data
    body["request_value"] = request_value
    payload = json.dumps(body, separators=(",", ":")).encode()
    host, _, port = HOST.partition(":")
    conn = http.client.HTTPConnection(host, int(port or 80), timeout=timeout)
    try:
        conn.request("POST", "/process_data.json", payload, {
            "Content-Type": "application/json; charset=UTF-8",
            "Connection": "close",
        })
        resp = json.loads(conn.getresponse().read())
    finally:
        conn.close()
    if resp.get("response_value") != "ok":
        raise RuntimeError(f"{command_type}/{request_value} 실패: {resp}")
    return resp.get("data")


def scan(wait):
    print("보일러가 주변 WiFi를 검색하는 중...", flush=True)
    call("kdone004", "scan", "set")
    for _ in range(4):
        time.sleep(wait)
        found = (call("kdone005", "scan", "get") or {}).get("scan list", [])
        if found:
            return found
    return []


def print_networks(networks):
    print(f"\n {'번호':>4}  {'WiFi 이름':24} {'신호':>8}  {'채널':>4}  보안")
    for i, n in enumerate(networks, 1):
        print(f" {i:>4}  {n['ssid']:24} {n['rssi']:>4} dBm  {n['ch']:>4}  {n['security']}")
    print("  (이름이 '....'로 보이는 건 한글 등 ASCII가 아닌 이름입니다)\n")


def ask_password(ssid):
    prompt = f"'{ssid}' 비밀번호: "
    # getpass reads the console directly; fall back to stdin when input is piped (tests)
    return getpass.getpass(prompt) if sys.stdin.isatty() else input(prompt)


def choose(networks):
    while True:
        raw = input(f"연결할 번호를 고르세요 (1-{len(networks)}, q=취소): ").strip().lower()
        if raw == "q":
            sys.exit("취소했습니다.")
        if raw.isdigit() and 1 <= int(raw) <= len(networks):
            return networks[int(raw) - 1]
        print("  목록에 있는 번호를 입력하세요.")


def join(target, password):
    # Same shape the app sends: a list of single-key objects, in this order.
    data = [
        {"ssid": target["ssid"]},
        {"password": password},
        {"bssid": target["bssid"]},
        {"ch": target["ch"]},
        {"security": target["security"]},
        {"pairwise": target["pairwise"]},
        {"group": target["group"]},
    ]
    call("kdone006", "join", "set", data)
    print(f"\n연결 요청을 보냈습니다: {target['ssid']} ({target['bssid']}, 채널 {target['ch']})")
    print("보일러가 접속하면 설정용 WiFi(NR40-xxxx)가 사라집니다. PC WiFi는 원래대로 돌려놓으세요.")


def main():
    global HOST
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="목록만 보여 주고 끝냅니다")
    ap.add_argument("--ssid", help="번호를 고르지 않고 이 WiFi로 바로 연결합니다")
    ap.add_argument("--password", help="생략하면 입력하라고 묻습니다(명령 기록에 안 남음)")
    ap.add_argument("--scan-wait", type=float, default=5.0)
    ap.add_argument("--host", default=HOST, help="보일러 주소 host[:port] (테스트할 때만 변경)")
    args = ap.parse_args()
    HOST = args.host

    print(SETUP_GUIDE)
    try:
        call("kdone001", "validproduct", "get")
        product = call("kdone003", "productid", "get")
    except OSError as exc:
        sys.exit(f"보일러({HOST})에 연결할 수 없습니다: {exc}\n"
                 "위 [준비]를 마친 뒤 다시 실행하세요. 설정 모드는 일정 시간이 지나면 꺼질 수 있습니다.")
    print(f"보일러 모듈: {product}")

    networks = scan(args.scan_wait)
    if not networks:
        sys.exit("보일러가 WiFi를 하나도 찾지 못했습니다. 다시 시도해 보세요.")

    if args.ssid:
        target = next((n for n in networks if n["ssid"] == args.ssid), None)
        if target is None:
            print_networks(networks)
            sys.exit(f"'{args.ssid}'가 목록에 없습니다. 보일러는 2.4GHz WiFi만 봅니다.")
    else:
        print_networks(networks)
        if args.list:
            return
        target = choose(networks)

    if target["security"].upper() in OPEN_SECURITY:
        password = ""
    elif args.password is not None:
        password = args.password
    else:
        password = ask_password(target["ssid"])
        if len(password) < 8:
            sys.exit("WPA 비밀번호는 8자 이상입니다. 다시 실행하세요.")
    join(target, password)


if __name__ == "__main__":
    main()
