# 상시 운영 배포 (Docker)

집 안 서버(MY-COMPUTER, CasaOS, `192.168.0.7`)에서 DNS와 보일러 서버를 24시간 돌리는 구성입니다.

| 구성 | 역할 | 포트 |
|---|---|---|
| **AdGuard Home** (CasaOS 앱, 권장) | 집 전체 DNS. "DNS 재작성"으로 `krst2.naviensmartcontrol.com` → `192.168.0.7`. 웹 관리 화면, 질의 기록, 광고 차단도 제공 | 53, 관리 화면 |
| `navien` (이 compose) | 나비엔 서버를 대신하는 보일러 서버(빌드 원본: `../server`)와 제어 API. 시간대는 `Asia/Seoul` | `HOST_IP:7000`, `HOST_IP:8080` |
| `dns` (dnsmasq, 선택) | AdGuard를 쓰지 않을 때만 사용. 같은 도메인 재작성만 하는 최소 DNS | `HOST_IP:53` |

> AdGuard Home과 dnsmasq는 둘 다 53번 포트를 쓰므로 **하나만** 켭니다. 기본 `docker compose up`은 dnsmasq를 띄우지 않습니다.

## 1. 보일러 서버 올리기

`navien_boiler` 폴더 **전체**를 서버로 복사합니다. 컨테이너를 `../server`에서 빌드하기 때문입니다.

```bash
cd navien_boiler/deploy
cp .env.example .env      # 처음 한 번
docker compose up -d --build
docker compose ps
```

`.env`의 `HOST_IP`는 서버의 고정 내부 IP입니다(기본값 `192.168.0.7`).
CasaOS 대시보드에는 따로 표시되지 않을 수 있지만, Docker 컨테이너로 정상 동작합니다.

## 1-1. DNS: CasaOS에 AdGuard Home 설치 (권장)

1. CasaOS 앱스토어에서 **AdGuard Home**을 설치합니다.
2. 처음 설정 화면(CasaOS 앱 아이콘을 누르거나 `http://192.168.0.7:3000`)에서 아래처럼 정합니다.
   - **관리 화면 포트:** 80과 8080은 피합니다. 80은 CasaOS 대시보드, 8080은 보일러 API가 씁니다. (예: `3000`)
   - **DNS 수신 인터페이스:** `enp1s0 - 192.168.0.7`, 포트 `53`.
     "모든 인터페이스"로 두면 서버 내부 DNS(systemd-resolved `127.0.0.53`, LXC `10.0.3.1`)와 53번 포트가 충돌할 수 있습니다.
3. **설정 → DNS 설정 → 업스트림 DNS**에 KT DNS를 넣습니다. 국내 사이트 CDN 연결이 가장 빠릅니다.
   ```
   168.126.63.1
   168.126.63.2
   ```
4. **필터 → DNS 재작성 → 추가:**
   - 도메인: `krst2.naviensmartcontrol.com`
   - 응답: `192.168.0.7`
5. (선택) **설정 → 일반 설정 → 쿼리 로그 보존 기간**을 짧게 둡니다. 기본적으로 집 안 모든 기기의 DNS 질의가 기록됩니다.

설치하다가 `address already in use`(53번) 오류가 나면, 2번의 DNS 수신 인터페이스를 `192.168.0.7`로 지정했는지 먼저 확인하세요.

## 1-2. DNS: dnsmasq 사용 (AdGuard를 안 쓸 때만)

```bash
docker compose --profile dnsmasq up -d --build
```

## 2. 공유기 설정 전에 동작 확인

아무 PC에서나 실행합니다.

```bash
python tools/dns_probe.py 192.168.0.7 53 krst2.naviensmartcontrol.com www.naver.com
```

- `krst2...`: A 레코드가 `192.168.0.7`이고, AAAA 레코드에 진짜 서버 주소가 나오지 않으면(`answers=[]` 또는 CNAME만) 정상입니다.
- `www.naver.com`: 정상 IP가 나오면 됩니다.
- 보일러 서버: `http://192.168.0.7:8080/status`가 `{"connected": false}`를 돌려주면 정상입니다(아직 보일러가 붙기 전).

**여기까지 확인한 뒤에** 공유기 설정을 바꾸세요. 순서를 바꾸면 집 인터넷이 끊깁니다.

## 3. ipTIME 공유기 설정 (AX3000SM 기준)

1. **서버 IP 고정:** 네트워크 관리 → DHCP 서버 설정 → 등록된 주소 관리에서 `192.168.0.7` ↔ `20:24:06:28:04:88`을 등록합니다.
   - 서버가 이전 주소를 계속 쓰면, 서버에서 임대를 지우고 다시 받습니다(NetworkManager 기준).
     ```bash
     sudo setsid nohup sh -c 'rm -f /var/lib/NetworkManager/*enp1s0*.lease; nmcli connection down "Wired connection 1"; sleep 2; nmcli connection up "Wired connection 1"' >/tmp/renew.log 2>&1 &
     ```
2. **DNS 변경:** 같은 **DHCP 서버 설정** 화면에서 DNS "수동입력"을 체크합니다.
   - 기본 DNS: `192.168.0.7`
   - 보조 DNS: `168.126.63.1`
3. IP 주소 대여 시간은 2시간 이상으로 둡니다. 1분처럼 짧게 두면 IoT 기기가 불안정해집니다.

> ⚠️ **"내부 네트워크 설정 → 허브/AP모드 내부 게이트웨이"는 체크하지 마세요.** 허브/AP 모드 전용 설정이라, 공유기 모드에서 켜면 집 네트워크가 끊깁니다.
>
> 보조 DNS를 KT로 두면 서버가 꺼져도 집 인터넷은 그대로 유지되고, 보일러는 나비엔 클라우드로 돌아갑니다. 보일러가 가끔 클라우드에 붙는다면 보조 DNS도 `192.168.0.7`로 바꾸세요. 대신 그 경우 서버가 꺼지면 집 전체 DNS가 멈춥니다.

## 4. 보일러를 집 WiFi로 옮기기 (순서 중요)

보일러 WiFi 등록은 **기기의 자체 AP에 폰을 붙여 앱으로 SSID/비밀번호를 넘기는 방식**입니다.
등록이 끝나면 앱은 보일러가 나비엔 클라우드에 접속했는지 확인합니다. 그래서 **클라우드가 보이는 상태에서 등록**하는 게 안전합니다.

1. 서버를 올리고 2번 확인까지 마칩니다. **공유기 DNS는 아직 KT 그대로** 둡니다.
2. PC `hosts`에서 `192.168.137.1 krst2.naviensmartcontrol.com` 줄을 삭제합니다.
3. 보일러를 **집 2.4GHz WiFi에 등록**합니다. 설정 모드는 보일러를 끈 상태에서 조절기 [+] 버튼을 3초간 누르면 켜집니다.
   스마트톡 앱으로 평소처럼 해도 되고, PC에서 `python tools/provision.py`로 해도 됩니다.
4. PC 핫스팟을 끕니다.
5. 3번 순서대로 **공유기 DNS를 `192.168.0.7`로 변경**합니다.
6. 보일러가 다시 접속하게 만듭니다. 보일러 전원 플러그를 10초 뺐다 꽂거나, 공유기 2.4GHz WiFi를 잠깐 껐다 켭니다.
   재접속할 때 DHCP로 새 DNS를 받고, 내 서버로 붙습니다.
7. `http://192.168.0.7:8080/status`에서 `"connected": true`를 확인합니다.

> **나중에 WiFi가 바뀌면:** 공유기를 바꾸더라도 **SSID와 비밀번호를 지금과 똑같이** 쓰면 보일러는 재등록 없이 알아서 붙습니다.
> 꼭 재등록해야 한다면 공유기 DNS 수동입력을 잠시 해제해 클라우드로 돌린 뒤 등록하고, 다시 켜면 됩니다.
> 앱이나 클라우드가 없을 때는 `tools/provision.py`로 PC에서 직접 등록할 수 있습니다(루트 README 참고). 이 방법은 클라우드를 확인하지 않으므로 DNS를 바꾼 상태에서도 그대로 됩니다.

## 로그

```bash
docker compose logs -f navien     # 보일러와 주고받은 프레임
ls data/                          # navien_server.log
```

## 되돌리기 (나비엔 클라우드로 복귀)

공유기 DHCP 서버 설정에서 DNS "수동입력"을 해제하고, 보일러 WiFi를 껐다 켭니다.
AdGuard Home은 그대로 두고 DNS 재작성 규칙만 끄거나 지워도 같은 효과가 있습니다.
