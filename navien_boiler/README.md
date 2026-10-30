# navien_boiler — 나비엔 NR-400 완전 로컬 제어

나비엔 스마트톡 **NR-400**(WiFi)을 나비엔 클라우드 없이 집 안 서버에서 제어합니다.
보일러 WiFi 모듈이 접속하는 서버 주소를 DNS로 내 서버로 돌리고, 내 서버가 나비엔 서버 역할을 대신합니다.

```
[NR-400 WiFi 모듈] ── DNS: krst2.naviensmartcontrol.com? ──▶ [dnsmasq] ──▶ "192.168.0.7"
        │
        └── TCP 7000 (평문 바이너리) ──▶ [navien_local_server] ◀── HTTP 8080 ── 나 / Home Assistant
```

## 결과 요약

| 항목 | 결과 |
|---|---|
| 통신 방식 | 평문 TCP, 암호화·인증 없음 → **서버를 대신할 수 있음** |
| 서버 주소 | `krst2.naviensmartcontrol.com:7000`, DNS로 조회(IP 하드코딩 아님) |
| 체크섬 | CRC-16/BUYPASS, 캡처한 모든 프레임에서 검증 |
| 실기기 테스트 | 로컬 서버로 접속·등록 성공. 온돌 39°C → 40°C → 외출 제어 성공. 이상 프레임 0건 |
| 상시 운영 | Docker(dnsmasq + 서버) 구성. 이 PC Docker에서 DNS·재생 테스트·시간 동기화 검증 |
| WiFi 등록 | 설정 모드 AP에 평문 HTTP/JSON으로 등록, 인증 없음 → **앱 없이 PC에서 등록 가능** (`tools/provision.py`) |

프로토콜 상세는 [docs/PROTOCOL.md](docs/PROTOCOL.md)를 보세요.

## 폴더 구조

```
navien_boiler/
├─ README.md                  ← 이 문서
├─ docs/
│  └─ PROTOCOL.md             프레임 구조, 명령표, 상태 필드, 접속 순서
├─ server/                    보일러 서버 (원본은 여기 하나)
│  ├─ navien_local_server.py  TCP 7000 서버 + HTTP 8080 제어 API
│  ├─ test_replay.py          실제 캡처를 재생해 진짜 서버 응답과 바이트 단위 비교
│  └─ Dockerfile              python:3.12-alpine, TZ=Asia/Seoul
├─ deploy/                    상시 운영용 Docker 구성
│  ├─ docker-compose.yml      dns + navien
│  ├─ .env.example            HOST_IP 등 (.env로 복사해서 사용, .env는 git 제외)
│  ├─ dns/                    dnsmasq 이미지
│  └─ README.md               서버 배포, ipTIME 설정, 보일러 재연결 절차
├─ tools/                     분석·점검 도구
│  ├─ decode.py               pcap → 프레임 해석, CRC 검증 (tshark 필요)
│  ├─ crc_search.py           체크섬 알고리즘 탐색
│  ├─ dns_probe.py            DNS 서버에 A/AAAA를 직접 질의해 확인
│  ├─ provision.py            앱 없이 보일러 WiFi 설정: 목록에서 번호 선택 + 비밀번호
│  ├─ test_provision.py       가짜 보일러로 provision.py 요청이 앱과 같은지 검증
│  ├─ capture_reconnect.ps1   PC 핫스팟에서 보일러 패킷 캡처 (Windows, Wireshark)
│  └─ compose.test.yml        Windows Docker Desktop에서 검증할 때 쓰는 오버라이드
└─ captures/                  분석에 쓴 원본 캡처 (pcapng, git 제외: 집 네트워크 정보 포함)
```

## 빠르게 쓰기

### 상시 운영 (권장)
[deploy/README.md](deploy/README.md)의 순서를 따르세요.
**서버에 올려 확인 → 공유기 DNS 변경 → 보일러를 집 WiFi에 연결** 순서가 중요합니다.

### PC 한 대로 테스트
1. Windows 모바일 핫스팟(2.4GHz)을 켜고 보일러를 연결합니다.
2. 관리자 권한으로 `hosts`에 `192.168.137.1 krst2.naviensmartcontrol.com`을 추가합니다.
3. 서버를 실행합니다.
   ```bash
   python server/navien_local_server.py --bind 0.0.0.0
   ```
4. 핫스팟을 껐다 켜면 보일러가 재접속하면서 이 PC로 붙습니다.

## 제어 API (HTTP 8080)

| 요청 | 동작 |
|---|---|
| `GET /status` | 접속 여부, 모드, 실내온도, 설정온도 (JSON) |
| `GET /set?temp=40` | 온돌 40°C (10~45°C, 0.5°C 단위. 범위 밖은 거부) |
| `GET /mode?name=off` / `on` / `away` | 끄기 / 켜기 / 외출 |
| `GET /refresh` | 상태 다시 요청 |

```bash
curl http://192.168.0.7:8080/status
curl "http://192.168.0.7:8080/set?temp=40"
```

API에는 인증이 없습니다. **8080 포트를 공유기 밖으로 열지 마세요.** 외부에서 쓰려면 Tailscale 같은 VPN을 쓰세요.

## 테스트

```bash
# 서버를 띄운 상태에서 (기본 7000/8080)
python server/test_replay.py
# Docker 등 다른 포트라면
python server/test_replay.py 17000 18080

# 캡처 해석
python tools/decode.py captures/login_01.pcapng
```

`test_replay.py`는 실제 보일러의 등록, 설정, 상태 프레임을 보내서 서버 응답이 진짜 나비엔 서버와 **바이트 단위로 같은지** 확인합니다. 온도 설정과 외출 명령 프레임도 같은 방식으로 비교합니다.

## 주의

- 로컬 서버에 붙어 있는 동안 **스마트톡 앱은 동작하지 않습니다.** 조절기에서 직접 조작하는 건 언제나 됩니다.
- 제어는 나비엔 서버가 보내던 명령(전원, 외출, 온돌 온도)만 그대로 사용합니다. 미해독 명령은 보내지 마세요.
- 보조 DNS를 KT로 두면 서버가 꺼졌을 때 보일러가 클라우드로 돌아갑니다(안전한 대체 경로).
- ipTIME의 **"허브/AP모드 내부 게이트웨이"** 옵션은 쓰지 마세요. 공유기 모드에서 켜면 네트워크가 끊깁니다.

## 되돌리기

공유기 DHCP 서버 설정에서 DNS 수동입력을 해제하거나, PC `hosts`의 해당 줄을 지운 뒤 보일러 WiFi를 재연결하면 나비엔 클라우드로 돌아갑니다.

## 앱 없이 보일러 WiFi 설정하기

스마트톡 앱이나 나비엔 클라우드가 없어도 PC에서 보일러 WiFi를 설정할 수 있습니다.

1. 조절기를 WiFi 설정 모드로 바꿉니다.
   **보일러를 끈 상태에서 조절기의 [+] 버튼을 3초간 누르면** 암호 없는 WiFi `NR40-xxxx`가 생깁니다.
2. PC를 그 WiFi에 연결합니다. "인터넷 없음"으로 표시돼도 정상입니다.
3. 스크립트를 실행합니다.
   ```bash
   python tools/provision.py
   ```
   보일러가 직접 검색한 WiFi 목록(보일러가 연결할 수 있는 2.4GHz만)이 번호와 함께 나옵니다.
   ```
    번호  WiFi 이름                신호    채널  보안
       1  jerry2                -55 dBm    03  WPA2-PSK
       2  iptime_kong           -72 dBm    08  WPA2-PSK
   연결할 번호를 고르세요 (1-2, q=취소): 1
   'jerry2' 비밀번호: ********
   ```
4. 번호를 고르고 비밀번호를 입력합니다. 비밀번호는 화면에 보이지 않고, 명령 기록에도 남지 않습니다.
5. 설정용 WiFi가 사라지면 완료입니다. PC의 WiFi 연결은 원래대로 돌려놓으세요.

목록만 보려면 `--list`, 번호를 고르지 않고 바로 연결하려면 `--ssid jerry2`를 씁니다.

보일러는 2.4GHz WiFi만 봅니다. 프로토콜은 [docs/PROTOCOL.md](docs/PROTOCOL.md#wifi-등록-프로비저닝)에 있습니다.

## 남은 일

- 예약표(281바이트), 온수 모드 등 미해독 부분 → [docs/PROTOCOL.md](docs/PROTOCOL.md#미해독)
- Home Assistant `climate` 엔티티 연동
