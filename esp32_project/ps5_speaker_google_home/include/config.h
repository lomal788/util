#pragma once

// PC 로 보내는 길. 둘 다 켜 두면 펌웨어를 다시 올리지 않고
// receiver.py 실행 방식만으로 고른다 (--serial COM11 = 유선, 옵션 없음 = Wi-Fi).
#define USE_UART 1
#define USE_WIFI 1

// 유선: 보드의 UART 단자. 48 kHz 스테레오 16 bit 가 약 1.92 Mbps 라 3 Mbaud 를 쓴다.
// USE_UART 가 1 이면 로그도 이 속도로 같이 나간다 (receiver.py 가 [S3] 로 보여 줌).
#define UART_BAUD 3000000

// ESP32-S3 는 2.4 GHz 만 된다. jerry5 는 5 GHz(채널 36)라 붙지 않는다.
#define WIFI_SSID "jerry2"
#define WIFI_PASS "qwert124!"
#define STREAM_PORT 4010

// PS5 의 헤드폰 음량을 S3 에서 적용할지. 0 이면 원본 크기 그대로 보내고 음량은 PC 에서 조절한다.
// 1 로 두면 PS5 음량 막대가 -60 ~ 0 dB 로 먹는다 (중간쯤이면 -35 dB 라 매우 작게 들림).
#define USB_APPLY_VOLUME 0

// 패킷 하나에 담는 길이. 48 kHz 스테레오 16 bit = 1 ms 당 192 바이트.
#define PACKET_MS 2
