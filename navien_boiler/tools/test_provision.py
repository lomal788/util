"""Run provision.py against a fake boiler that replays the captured responses,
and check that every request body matches what the Smart-Tok app sent."""
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Request bodies the app sent (captures/PCAPdroid_30_Oct_14_35_40.pcap), password replaced.
APP_REQUESTS = [
    '{"command_id":"kdone001","command_type":"validproduct","request_value":"get"}',
    '{"command_id":"kdone003","command_type":"productid","request_value":"get"}',
    '{"command_id":"kdone004","command_type":"scan","request_value":"set"}',
    '{"command_id":"kdone005","command_type":"scan","request_value":"get"}',
    '{"command_id":"kdone006","command_type":"join","data":[{"ssid":"jerry2"},{"password":"TESTPASS"},'
    '{"bssid":"B0:38:6C:38:CB:D8"},{"ch":"03"},{"security":"WPA2-PSK"},{"pairwise":"CCMP"},{"group":"CCMP"}],'
    '"request_value":"set"}',
]
SCAN = {"scan list": [
    {"no": "00", "ssid": "jerry2", "bssid": "B0:38:6C:38:CB:D8", "ch": "03", "rssi": "-55",
     "security": "WPA2-PSK", "pairwise": "CCMP", "group": "CCMP", "wps": "WPS_OFF", "mode": "b/g/n"},
    {"no": "01", "ssid": "iptime_kong", "bssid": "B0:38:6C:60:D5:02", "ch": "08", "rssi": "-72",
     "security": "WPA2-PSK", "pairwise": "CCMP", "group": "CCMP", "wps": "WPS_OFF", "mode": "b/g/n"},
]}
RESPONSES = {
    "validproduct": "", "productid": "047863a6e14a4204", "scan": None, "join": "",
}
received = []


class FakeBoiler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"])).decode()
        received.append(body)
        req = json.loads(body)
        kind = req["command_type"]
        data = SCAN if kind == "scan" and req["request_value"] == "get" else RESPONSES[kind] or ""
        out = json.dumps({"command_id": req["command_id"].replace("kdone", "incte"),
                          "command_type": kind, "response_value": "ok", "data": data}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *_):
        pass


def run_case(name, port, extra_args, stdin=None):
    received.clear()
    script = Path(__file__).with_name("provision.py")
    run = subprocess.run(
        [sys.executable, str(script), "--host", f"127.0.0.1:{port}", "--scan-wait", "0.1", *extra_args],
        input=stdin, capture_output=True, text=True, encoding="utf-8", timeout=30,
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    )
    ok = run.returncode == 0 and received == APP_REQUESTS
    print(f"=== {name}: {'OK' if ok else 'FAIL'} (exit {run.returncode})")
    if not ok:
        print(run.stdout, run.stderr)
        for want, got in zip(APP_REQUESTS, received + [""] * len(APP_REQUESTS)):
            if want != got:
                print(f"  want {want}\n  got  {got}")
    return ok, run.stdout


def main():
    srv = HTTPServer(("127.0.0.1", 0), FakeBoiler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_port
    results = []

    ok, _ = run_case("--ssid (non-interactive)", port, ["--ssid", "jerry2", "--password", "TESTPASS"])
    results.append(ok)

    # interactive: an out-of-range pick first, then 1, then the password
    ok, out = run_case("interactive pick", port, [], stdin="9\n1\nTESTPASS\n")
    results.append(ok and "목록에 있는 번호" in out and "iptime_kong" in out)
    print(out[out.index(" 번호"):out.index("연결할 번호")].rstrip() if " 번호" in out else out)

    received.clear()
    srv.shutdown()
    print("ALL PASSED" if all(results) else "FAILED")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
