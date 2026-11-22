// PS5 (USB 스피커로 인식) -> ESP32-S3 -> PC (pc_receiver/receiver.py)
// PC 로는 UART(유선)와 Wi-Fi UDP 두 길로 보낸다. config.h 에서 켜고 끈다.

#include <Arduino.h>
#include <freertos/stream_buffer.h>

#include "USB.h"
#include "config.h"
#include "usb_speaker.h"

#if USE_WIFI
#include <WiFi.h>
#include <WiFiUdp.h>
#endif

#define PACKET_BYTES (PACKET_MS * 192)
#define PCM_BUFFER_BYTES 8192

static StreamBufferHandle_t s_pcm;
static volatile uint32_t s_dropped;
static volatile uint32_t s_usb_bytes;

static void on_pcm(const uint8_t* pcm, size_t len) {
  s_usb_bytes += len;
  // 일부만 들어가면 프레임 경계가 어긋나므로 자리가 모자라면 통째로 버린다.
  if (xStreamBufferSpacesAvailable(s_pcm) >= len) {
    xStreamBufferSend(s_pcm, pcm, len, 0);
  } else {
    s_dropped++;
  }
}

#if USE_UART
static void uart_send(uint16_t seq, const uint8_t* pcm, size_t n) {
  // UART 는 바이트 흐름이라 길이를 실어야 한다. 로그 글자와 섞여도 받는 쪽이
  // 패킷 머리를 가려낼 수 있게 길이의 보수를 같이 보낸다.
  // UART 에는 오류 검출이 없어서, 깨진 패킷이 잡음으로 재생되지 않게 합계도 싣는다.
  uint16_t len = (uint16_t)n;
  uint16_t inv = (uint16_t)~len;
  uint16_t sum = 0;
  for (size_t i = 0; i < n; i++) sum += pcm[i];
  const uint8_t hdr[10] = {
      0xA5, 0x5A,
      (uint8_t)(seq & 0xFF), (uint8_t)(seq >> 8),
      (uint8_t)(len & 0xFF), (uint8_t)(len >> 8),
      (uint8_t)(inv & 0xFF), (uint8_t)(inv >> 8),
      (uint8_t)(sum & 0xFF), (uint8_t)(sum >> 8),
  };
  Serial.write(hdr, sizeof(hdr));
  Serial.write(pcm, n);
}
#endif

#if USE_WIFI
#define CLIENT_TIMEOUT_MS 3000

static const char HELLO[] = "PS5SPK_HELLO";
static const char BEACON[] = "PS5SPK_BEACON";

static WiFiUDP s_udp;
static bool s_udp_open;
static IPAddress s_client_ip;
static uint16_t s_client_port;
static bool s_client;
static uint32_t s_client_seen_ms;

static void poll_hello(uint32_t now) {
  char buf[32];
  while (s_udp.parsePacket() > 0) {
    int n = s_udp.read(buf, sizeof(buf));
    if (n == (int)strlen(HELLO) && memcmp(buf, HELLO, n) == 0) {
      IPAddress ip = s_udp.remoteIP();
      uint16_t port = s_udp.remotePort();
      if (!s_client || ip != s_client_ip || port != s_client_port) {
        Serial.printf("receiver: %s:%u\n", ip.toString().c_str(), port);
      }
      s_client_ip = ip;
      s_client_port = port;
      s_client = true;
      // 호출자의 now 와 같은 시각을 써야 한다. millis() 를 다시 읽으면 now 보다 커져서
      // 바로 아래 시간 초과 검사의 뺄셈이 음수로 넘어간다.
      s_client_seen_ms = now;
    }
    s_udp.flush();
  }
}

static void send_beacon() {
  s_udp.beginPacket(WiFi.broadcastIP(), STREAM_PORT);
  s_udp.write((const uint8_t*)BEACON, strlen(BEACON));
  s_udp.endPacket();
}

static void wifi_service(uint32_t now) {
  static uint32_t last_poll_ms, last_beacon_ms, last_wait_ms;

  if (WiFi.status() != WL_CONNECTED) {
    if (s_udp_open) {
      s_udp.stop();
      s_udp_open = false;
      s_client = false;
      Serial.println("wifi lost");
    }
    if (now - last_wait_ms >= 5000) {
      last_wait_ms = now;
      Serial.printf("wifi connecting to %s (status %d)\n", WIFI_SSID, (int)WiFi.status());
    }
    return;
  }
  if (!s_udp_open) {
    s_udp.begin(STREAM_PORT);
    s_udp_open = true;
    Serial.printf("wifi ok: %s\n", WiFi.localIP().toString().c_str());
  }

  if (now - last_poll_ms >= 100) {
    last_poll_ms = now;
    poll_hello(now);
    if (s_client && now - s_client_seen_ms > CLIENT_TIMEOUT_MS) {
      s_client = false;
      Serial.println("receiver timeout");
    }
  }
  if (now - last_beacon_ms >= 1000) {
    last_beacon_ms = now;
    send_beacon();
  }
}

static void wifi_send(uint16_t seq, const uint8_t* pcm, size_t n) {
  if (!s_udp_open || !s_client) return;
  const uint8_t hdr[4] = {0xA5, 0x5A, (uint8_t)(seq & 0xFF), (uint8_t)(seq >> 8)};
  s_udp.beginPacket(s_client_ip, s_client_port);
  s_udp.write(hdr, sizeof(hdr));
  s_udp.write(pcm, n);
  s_udp.endPacket();
}
#endif

void setup() {
#if USE_UART
  // 송신 버퍼가 없으면 패킷을 다 내보낼 때까지 loop 가 멈춘다.
  Serial.setTxBufferSize(8192);
  Serial.begin(UART_BAUD);
#else
  Serial.begin(115200);
#endif

  s_pcm = xStreamBufferCreate(PCM_BUFFER_BYTES, PACKET_BYTES);

  USB.VID(0x303A);
  USB.PID(0x8155);
  USB.manufacturerName("DIY");
  USB.productName("PS5 WiFi Speaker");
  USB.usbClass(0);
  USB.usbSubClass(0);
  USB.usbProtocol(0);
  if (!usb_speaker_begin(on_pcm)) Serial.println("usb speaker init failed");
  USB.begin();

#if USE_WIFI
  WiFi.mode(WIFI_STA);
  // 절전 모드에서는 패킷이 비콘 주기 단위로 몰려 나가 지연이 튄다.
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
#endif
}

void loop() {
  static uint8_t pcm[PACKET_BYTES];
  static size_t fill;
  static uint16_t seq;
  static uint32_t last_stat_ms, stat_bytes;
  static bool was_streaming;

  // 스트림 버퍼는 데이터가 조금이라도 있으면 바로 돌려주므로, 패킷 하나가 찰 때까지 모은다.
  size_t got = xStreamBufferReceive(s_pcm, pcm + fill, PACKET_BYTES - fill, pdMS_TO_TICKS(20));
  fill += got;
  size_t n = 0;
  if (fill == PACKET_BYTES || (got == 0 && fill > 0)) {
    n = fill;
    fill = 0;
  }
  uint32_t now = millis();

#if USE_WIFI
  wifi_service(now);
#endif

  bool streaming = usb_speaker_streaming();
  if (streaming != was_streaming) {
    was_streaming = streaming;
    Serial.println(streaming ? "usb stream start" : "usb stream stop");
  }
  static int16_t last_volume = INT16_MIN;
  static bool last_muted;
  int16_t volume = usb_speaker_volume();
  bool muted = usb_speaker_muted();
  if (volume != last_volume || muted != last_muted) {
    last_volume = volume;
    last_muted = muted;
    Serial.printf("usb volume %.1f dB%s\n", volume / 256.0f, muted ? " (muted)" : "");
  }
  if (now - last_stat_ms >= 5000) {
    uint32_t elapsed = now - last_stat_ms;
    last_stat_ms = now;
    uint32_t total = s_usb_bytes;
    if (streaming) {
      Serial.printf("usb %u frames/s, dropped %u\n", (unsigned)((total - stat_bytes) / 4 * 1000 / elapsed), (unsigned)s_dropped);
    }
    stat_bytes = total;
  }

  if (n == 0) return;

#if USE_UART
  uart_send(seq, pcm, n);
#endif
#if USE_WIFI
  wifi_send(seq, pcm, n);
#endif
  seq++;
}
