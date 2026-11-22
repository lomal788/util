# PS5 USB 스피커 → PC 재생 (ESP32-S3)

ESP32-S3를 PS5에 USB 스피커로 인식시키고, 받은 소리를 PC로 넘겨 PC 스피커로 재생한다.
PS5는 블루투스 오디오를 지원하지 않아서, PC 스피커를 PS5 스피커로 쓰려고 만들었다.

```
PS5 ──USB──▶ ESP32-S3 ──UART(유선) 또는 Wi-Fi──▶ PC (receiver.py) ──▶ 스피커
```

- 소리 형식: 48 kHz, 스테레오, 16 bit PCM. 압축 없이 그대로 보낸다.
- 전체 지연: 유선 기준 약 35~40 ms (구간별 값을 더한 추정). 블루투스 스피커는 150~300 ms.
- 폴더 이름의 `google_home`은 처음 구상의 흔적이다. 구글홈으로 보내는 기능은 없다.

## 준비물

| 항목 | 내용 |
|---|---|
| 보드 | ESP32-S3 개발보드 (N8R2, N16R8 모두 가능). USB 단자가 `UART`와 `USB(OTG)` 두 개인 것 |
| 케이블 | 데이터선이 있는 USB 케이블 2개. PS5 쪽은 A-to-C 권장 |
| PC | Windows, Python 3, PlatformIO |

## 연결

| 보드 단자 | 연결 대상 | 용도 |
|---|---|---|
| `USB` / `OTG` | PS5 USB 단자 | PS5가 스피커로 인식. 전원도 여기서 받음 |
| `UART` / `COM` | PC | 펌웨어 업로드, 유선으로 소리 전송 |

Wi-Fi로만 쓸 때는 `UART` 케이블이 없어도 된다.

## 펌웨어 올리기

1. `include/config.h`에서 Wi-Fi 이름과 비밀번호를 넣는다. ESP32-S3는 2.4 GHz만 된다.
2. `UART` 단자를 PC에 연결하고 올린다.

```
pio run -t upload --upload-port COM11
```

`receiver.py`가 같은 포트를 쓰고 있으면 올라가지 않는다. 먼저 끈다.

### config.h 설정

| 항목 | 기본값 | 뜻 |
|---|---|---|
| `USE_UART` | 1 | 유선(UART)으로 내보냄 |
| `USE_WIFI` | 1 | Wi-Fi UDP로 내보냄 |
| `UART_BAUD` | 3000000 | 유선 속도. 소리만 약 1.92 Mbps라 3 Mbaud가 필요 |
| `USB_APPLY_VOLUME` | 0 | PS5 헤드폰 음량을 S3에서 적용할지. 0이면 원본 크기 그대로 |
| `PACKET_MS` | 2 | 패킷 하나에 담는 길이 (ms) |

유선과 Wi-Fi를 둘 다 켜 두면 펌웨어를 다시 올리지 않고 PC에서 실행 방식만으로 고른다.

## PC에서 재생

```
cd pc_receiver
pip install -r requirements.txt

python receiver.py --serial COM11                  # 유선
python receiver.py --serial COM11 --buffer-ms 15   # 유선, 지연을 조금 더 줄임
python receiver.py                                 # Wi-Fi (S3를 자동으로 찾음)
python receiver.py --ip 192.168.0.28               # Wi-Fi, 주소 지정
python receiver.py --list                          # 출력 장치 목록
```

Wi-Fi로 처음 실행하면 Windows 방화벽 허용을 눌러야 한다.

| 옵션 | 기본값 | 뜻 |
|---|---|---|
| `--serial PORT` | 없음 | 유선으로 받을 COM 포트. 생략하면 Wi-Fi |
| `--baud` | 3000000 | 유선 속도. `UART_BAUD`와 같아야 함 |
| `--ip` | 자동 | Wi-Fi일 때 S3 주소 |
| `--buffer-ms` | 유선 20, Wi-Fi 40 | 수신 버퍼 목표 길이. 작을수록 지연이 줄고 끊기기 쉬움 |
| `--block-ms` | 유선 5, Wi-Fi 10 | 오디오 콜백 길이 |
| `--gain-db` | 0 | 받은 소리를 키우는 양. 넘치는 값은 잘림 |
| `--device` | WASAPI 기본 출력 | 출력 장치 번호나 이름 |

### PS5 설정

1. 설정 → 사운드 → 오디오 출력 → 출력 기기에서 `PS5 WiFi Speaker`를 고른다. PS5는 USB 오디오를 전부 "USB 헤드폰"으로 표시한다.
2. 같은 메뉴의 "헤드폰으로 출력"을 "모든 오디오"로 둔다.

### 화면에 나오는 숫자

```
[S3] usb 48000 frames/s, dropped 0
peak -12.3 dBFS | buffer min  8.9 ms | lost 0 | corrupt 0 | underrun 0 | resync 0
```

| 항목 | 뜻 | 정상 |
|---|---|---|
| `usb ... frames/s` | S3가 PS5에서 받는 속도 | 48000 (47990도 정상) |
| `dropped` | S3 안에서 버린 패킷 | 0 |
| `peak` | 받은 소리의 최대 크기 | `silent`면 PS5가 무음을 보내는 중, `CLIP`이면 `--gain-db`가 큼 |
| `buffer min` | 5초 동안 버퍼가 가장 적게 남은 양 | 콜백 길이보다 넉넉히 클 것 |
| `lost` | 전송 중 빠진 패킷 | 0 |
| `corrupt` | 유선에서 깨져서 버린 패킷 | 0 |
| `underrun` | 버퍼가 비어 소리가 끊긴 횟수 | 0 |
| `resync` | 버퍼가 크게 밀려 건너뛴 횟수 | 시작할 때 1 정도 |

`underrun`이 계속 오르면 `--buffer-ms`를 올린다. 이 PC에서는 유선 15가 안정적이었고 10은 계속 끊겼다.

## 동작 방식

### USB 쪽 (`src/usb_speaker.cpp`)

USB Audio Class 1.0 스피커로 동작한다. Arduino 코어 2.0.x에 들어 있는 TinyUSB는 오디오 클래스 없이 빌드돼 있어서, `usbd_app_driver_get_cb()`로 클래스 드라이버를 직접 등록했다.

이 코어의 USB 드라이버(`dcd_esp32sx`)는 64 바이트가 넘는 등시성 수신을 제대로 처리하지 못해서 레지스터를 직접 만지는 우회가 세 군데 있다.

| 문제 | 우회 |
|---|---|
| 수신 FIFO가 208 바이트라 192 바이트 오디오 패킷이 들어가지 않음 | 버스 리셋마다 FIFO를 128 워드로 키움 |
| 전송 크기를 7 bit로 잘라 써넣음 | 전송 전에 크기 레지스터를 직접 써 둠 |
| 등시성 수신에 필요한 짝/홀 프레임 지정을 하지 않음 | 전송을 걸 때마다 직접 지정 |

이 우회가 코어 버전에 묶여 있어서 `platformio.ini`에서 플랫폼을 `espressif32@6.7.0`으로 고정했다. 코어 3.x는 USB 드라이버가 달라 그대로는 맞지 않는다.

### PC로 보내는 쪽 (`src/main.cpp`)

| 경로 | 형식 |
|---|---|
| UART | 머리 10 바이트(`A5 5A`, 순번, 길이, 길이의 보수, 합계) + PCM. 로그 글자도 같은 선으로 나감 |
| Wi-Fi | UDP 포트 4010. 머리 4 바이트(`A5 5A`, 순번) + PCM |

Wi-Fi는 S3가 1초마다 방송 신호를 보내고, PC가 응답하면 그 주소로 소리를 보낸다. 3초 동안 응답이 없으면 멈춘다.

### PC 재생 (`pc_receiver/receiver.py`)

PS5와 PC 사운드카드의 클럭이 조금 달라 버퍼가 서서히 차거나 빈다. 콜백마다 프레임 하나를 버리거나 되풀이해 목표 길이 근처로 되돌린다.

## 측정 결과

| 항목 | 결과 |
|---|---|
| 유선 무손실 | 129초, 24.8 MB를 Wi-Fi 경로와 바이트 단위로 대조해 불일치 0, 누락 0 |
| 유선 장시간 | 약 6분 실행 중 전송 오류 1회 (10 ms쯤 끊김) |
| Wi-Fi | 누락은 0~2 패킷/분 수준, 20 ms 넘는 멈춤이 가끔 있고 최대 66 ms |
| Windows 출력 지연 | WASAPI 공유 모드 22 ms |

유선 지연 추정: USB 1 + 패킷 묶기 2 + UART 2~3 + 수신 버퍼 10~15 + Windows 출력 22 = 약 35~40 ms.

## 알려진 문제

- **게임 소리만 안 나올 때**: 게임이 켜진 상태에서 보드가 재시작되면(펌웨어 업로드 등) OS 소리는 나는데 게임 소리는 무음으로 올 때가 있었다. USB를 뽑았다 꽂거나 게임을 다시 켠다. 원인은 확정하지 못했다.
- **시리얼 모니터로 로그를 볼 수 없음**: `USE_UART`가 1이면 로그도 3 Mbaud로 나가고 오디오와 섞인다. `receiver.py`가 `[S3]`를 붙여 보여 준다.
- **WASAPI 독점 모드는 쓰지 않음**: 지연을 줄이려고 시도했으나, 이 PC(Realtek)에서 콜백이 멈춰 삐 소리만 나고 Windows 오디오 서비스가 죽었다.
- **PS5 음량 막대가 듣지 않음**: `USB_APPLY_VOLUME`이 0이라 무시한다. 음량은 PC에서 조절한다.
- **단자가 하나뿐인 보드**: 그 단자가 OTG라서 업로드할 때 BOOT 버튼을 누른 채 RESET을 눌러 다운로드 모드로 넣어야 하고, 유선 전송은 쓸 수 없다.

## 폴더 구성

```
platformio.ini           빌드 설정 (플랫폼 버전 고정)
include/config.h         Wi-Fi, 전송 경로 설정
src/usb_speaker.cpp/.h   USB 스피커 드라이버
src/main.cpp             UART · Wi-Fi 전송
pc_receiver/receiver.py  PC 재생 프로그램
```
