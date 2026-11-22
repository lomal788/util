// USB Audio Class 1.0 스피커 (48 kHz, 스테레오, 16 bit).
//
// Arduino 코어 2.0.x 의 TinyUSB 는 오디오 클래스 없이 빌드돼 있어서,
// usbd_app_driver_get_cb() 로 클래스 드라이버를 직접 등록한다.

#include "usb_speaker.h"

#include <Arduino.h>
#include <math.h>
#include <string.h>

#include "config.h"
#include "esp32-hal-tinyusb.h"
#include "tusb.h"
#include "device/usbd_pvt.h"
#include "soc/usb_struct.h"

#define SAMPLE_RATE 48000
// 48 프레임(192 바이트) + 여유 1 프레임
#define EP_SIZE 196

#define ID_INPUT_TERMINAL 1
#define ID_FEATURE_UNIT 2
#define ID_OUTPUT_TERMINAL 3

#define UAC_SET_CUR 0x01
#define UAC_GET_CUR 0x81
#define UAC_GET_MIN 0x82
#define UAC_GET_MAX 0x83
#define UAC_GET_RES 0x84

#define FU_MUTE_CONTROL 0x01
#define FU_VOLUME_CONTROL 0x02
#define EP_SAMPLING_FREQ_CONTROL 0x01

// 음량 단위는 1/256 dB
#ifndef USB_VOLUME_MIN_DB
#define USB_VOLUME_MIN_DB (-60)
#endif
#define VOLUME_MIN (USB_VOLUME_MIN_DB * 256)
#define VOLUME_MAX 0
#define VOLUME_RES 256

// 출력 터미널 종류 (0x0301 스피커, 0x0302 헤드폰) 와 음량 조절 유닛 유무.
#ifndef USB_TERMINAL_TYPE
#define USB_TERMINAL_TYPE 0x0301
#endif
#ifndef USB_FEATURE_UNIT
#define USB_FEATURE_UNIT 1
#endif

#if USB_FEATURE_UNIT
#define DESC_LEN 101
#define AC_TOTAL_LEN 40
#define OUTPUT_SOURCE_ID ID_FEATURE_UNIT
#else
#define DESC_LEN 91
#define AC_TOTAL_LEN 30
#define OUTPUT_SOURCE_ID ID_INPUT_TERMINAL
#endif

// 15 + 2 * (EP_SIZE / 4) + 2 * (OUT 엔드포인트 수 7)
#define RX_FIFO_WORDS 128
#define EP0_TX_FIFO_WORDS 16

static usb_speaker_pcm_cb_t s_cb;

static uint8_t s_itf_as = 0xFF;
static uint8_t s_ep_out;
static tusb_desc_endpoint_t const* s_ep_desc;
static bool s_ep_open;
static volatile uint8_t s_alt;

static bool s_mute;
static int16_t s_volume = VOLUME_MAX;
static int32_t s_gain_q15 = 32768;

static uint8_t s_ctrl_buf[8];
CFG_TUSB_MEM_ALIGN static uint8_t s_rx_buf[EP_SIZE];

static void update_gain() {
  if (s_mute) {
    s_gain_q15 = 0;
    return;
  }
#if !USB_APPLY_VOLUME
  s_gain_q15 = 32768;
  return;
#endif
  if (s_volume == (int16_t)0x8000) {
    s_gain_q15 = 0;
    return;
  }
  int32_t g = lroundf(32768.0f * powf(10.0f, (s_volume / 256.0f) / 20.0f));
  s_gain_q15 = constrain(g, 0, 32768);
}

static uint16_t descriptor_cb(uint8_t* dst, uint8_t* itf) {
  uint8_t ac = *itf;
  uint8_t as = ac + 1;
  *itf += 2;

  s_ep_out = tinyusb_get_free_out_endpoint();
  if (s_ep_out == 0) return 0;

  const uint8_t desc[DESC_LEN] = {
      // AudioControl 인터페이스
      9, TUSB_DESC_INTERFACE, ac, 0, 0, TUSB_CLASS_AUDIO, 0x01, 0x00, 0,
      // AC 헤더: bcdADC 1.00, 스트리밍 인터페이스 1 개
      9, 0x24, 0x01, 0x00, 0x01, AC_TOTAL_LEN, 0, 1, as,
      // 입력 터미널: USB 스트리밍, 2 채널 (L, R)
      12, 0x24, 0x02, ID_INPUT_TERMINAL, 0x01, 0x01, 0, 2, 0x03, 0x00, 0, 0,
#if USB_FEATURE_UNIT
      // 피처 유닛: 마스터 음소거 + 음량
      10, 0x24, 0x06, ID_FEATURE_UNIT, ID_INPUT_TERMINAL, 1, 0x03, 0x00, 0x00, 0,
#endif
      // 출력 터미널
      9, 0x24, 0x03, ID_OUTPUT_TERMINAL, (uint8_t)(USB_TERMINAL_TYPE & 0xFF), (uint8_t)(USB_TERMINAL_TYPE >> 8), 0, OUTPUT_SOURCE_ID, 0,

      // AudioStreaming 인터페이스, alt 0 (대역폭 0)
      9, TUSB_DESC_INTERFACE, as, 0, 0, TUSB_CLASS_AUDIO, 0x02, 0x00, 0,
      // AudioStreaming 인터페이스, alt 1
      9, TUSB_DESC_INTERFACE, as, 1, 1, TUSB_CLASS_AUDIO, 0x02, 0x00, 0,
      // AS 일반: 입력 터미널에 연결, PCM
      7, 0x24, 0x01, ID_INPUT_TERMINAL, 1, 0x01, 0x00,
      // 포맷 타입 I: 2 채널, 2 바이트, 16 bit, 주파수 1 개
      11, 0x24, 0x02, 0x01, 2, 2, 16, 1,
      (uint8_t)(SAMPLE_RATE & 0xFF), (uint8_t)((SAMPLE_RATE >> 8) & 0xFF), (uint8_t)((SAMPLE_RATE >> 16) & 0xFF),
      // 등시성 OUT 엔드포인트 (adaptive), 1 ms 간격
      9, TUSB_DESC_ENDPOINT, s_ep_out, 0x09, (uint8_t)(EP_SIZE & 0xFF), (uint8_t)(EP_SIZE >> 8), 1, 0, 0,
      // 클래스 전용 엔드포인트: 주파수 제어 없음
      7, 0x25, 0x01, 0x00, 0, 0, 0,
  };
  memcpy(dst, desc, DESC_LEN);
  return DESC_LEN;
}

static void arm_rx(uint8_t rhport) {
  // 구 DCD(dcd_esp32sx)는 OUT 전송 크기를 7 bit 로 잘라 OR 로만 써넣는다.
  // 64 바이트가 넘는 패킷은 크기를 먼저 써 두어야 올바른 값이 남는다.
  USB0.out_ep_reg[s_ep_out].doeptsiz = (1u << 19) | EP_SIZE;

  if (!usbd_edpt_xfer(rhport, s_ep_out, s_rx_buf, EP_SIZE)) return;

  // 등시성 OUT 은 다음 프레임의 짝/홀을 맞춰 줘야 패킷을 받는데 구 DCD 는 이를 하지 않는다.
  // dsts bit 8 = 현재 프레임 번호의 최하위 비트, doepctl bit 28/29 = 짝수/홀수 프레임 지정.
  uint32_t odd_now = USB0.dsts & (1u << 8);
  USB0.out_ep_reg[s_ep_out].doepctl |= odd_now ? (1u << 28) : (1u << 29);
}

static void set_alt(uint8_t rhport, uint8_t alt) {
  s_alt = alt;
  // 구 DCD 에는 엔드포인트를 닫는 함수가 없다. alt 0 에서는 열어 둔 채 수신만 무시한다.
  if (alt == 0) return;

  if (!s_ep_open) {
    if (s_ep_desc == NULL || !usbd_edpt_open(rhport, s_ep_desc)) return;
    s_ep_open = true;
  }
  if (!usbd_edpt_busy(rhport, s_ep_out)) arm_rx(rhport);
}

static void uac_init(void) {}

static void uac_reset(uint8_t rhport) {
  (void)rhport;
  s_alt = 0;
  s_ep_open = false;

  // 구 DCD 는 버스 리셋마다 수신 FIFO 를 52 워드(208 바이트)로 잡는데,
  // SETUP 용 예약분을 빼면 192 바이트 오디오 패킷이 들어가지 않는다.
  // 수신 FIFO 를 키우고 바로 뒤에 붙는 EP0 송신 FIFO 시작 위치를 같이 옮긴다.
  USB0.grxfsiz = RX_FIFO_WORDS;
  USB0.gnptxfsiz = (EP0_TX_FIFO_WORDS << 16) | RX_FIFO_WORDS;
}

static uint16_t uac_open(uint8_t rhport, tusb_desc_interface_t const* itf, uint16_t max_len) {
  (void)rhport;
  if (itf->bInterfaceClass != TUSB_CLASS_AUDIO) return 0;

  // 같은 인터페이스 번호의 alt 설정과 거기 딸린 디스크립터까지 한 번에 가져간다.
  uint8_t const* start = (uint8_t const*)itf;
  uint8_t const* end = start + max_len;
  uint8_t const* p = tu_desc_next(start);
  while (p < end) {
    if (tu_desc_type(p) == TUSB_DESC_INTERFACE) {
      if (((tusb_desc_interface_t const*)p)->bInterfaceNumber != itf->bInterfaceNumber) break;
    } else if (tu_desc_type(p) == TUSB_DESC_ENDPOINT) {
      s_ep_desc = (tusb_desc_endpoint_t const*)p;
    }
    p = tu_desc_next(p);
  }

  if (itf->bInterfaceSubClass == 0x02) {
    s_itf_as = itf->bInterfaceNumber;
    s_alt = 0;
    s_ep_open = false;
  }
  return (uint16_t)(p - start);
}

static bool class_request(uint8_t rhport, uint8_t stage, tusb_control_request_t const* req) {
  const uint8_t recipient = req->bmRequestType_bit.recipient;
  const uint8_t entity = tu_u16_high(req->wIndex);
  const uint8_t cs = tu_u16_high(req->wValue);

  if (req->bmRequestType_bit.direction == TUSB_DIR_OUT) {
    if (req->bRequest != UAC_SET_CUR || req->wLength > sizeof(s_ctrl_buf)) return false;
    if (stage == CONTROL_STAGE_SETUP) return tud_control_xfer(rhport, req, s_ctrl_buf, req->wLength);
    if (stage == CONTROL_STAGE_DATA && recipient == TUSB_REQ_RCPT_INTERFACE && entity == ID_FEATURE_UNIT) {
      if (cs == FU_MUTE_CONTROL) {
        s_mute = s_ctrl_buf[0] != 0;
      } else if (cs == FU_VOLUME_CONTROL) {
        s_volume = (int16_t)(s_ctrl_buf[0] | (s_ctrl_buf[1] << 8));
      }
      update_gain();
    }
    return true;
  }

  if (stage != CONTROL_STAGE_SETUP) return true;

  uint16_t len = 0;
  if (recipient == TUSB_REQ_RCPT_INTERFACE && entity == ID_FEATURE_UNIT) {
    if (cs == FU_MUTE_CONTROL && req->bRequest == UAC_GET_CUR) {
      s_ctrl_buf[0] = s_mute;
      len = 1;
    } else if (cs == FU_VOLUME_CONTROL) {
      int16_t v;
      switch (req->bRequest) {
        case UAC_GET_CUR: v = s_volume; break;
        case UAC_GET_MIN: v = VOLUME_MIN; break;
        case UAC_GET_MAX: v = VOLUME_MAX; break;
        case UAC_GET_RES: v = VOLUME_RES; break;
        default: return false;
      }
      s_ctrl_buf[0] = (uint8_t)(v & 0xFF);
      s_ctrl_buf[1] = (uint8_t)((v >> 8) & 0xFF);
      len = 2;
    } else {
      return false;
    }
  } else if (recipient == TUSB_REQ_RCPT_ENDPOINT && cs == EP_SAMPLING_FREQ_CONTROL && req->bRequest == UAC_GET_CUR) {
    s_ctrl_buf[0] = (uint8_t)(SAMPLE_RATE & 0xFF);
    s_ctrl_buf[1] = (uint8_t)((SAMPLE_RATE >> 8) & 0xFF);
    s_ctrl_buf[2] = (uint8_t)((SAMPLE_RATE >> 16) & 0xFF);
    len = 3;
  } else {
    return false;
  }
  return tud_control_xfer(rhport, req, s_ctrl_buf, len);
}

static bool uac_control_xfer_cb(uint8_t rhport, uint8_t stage, tusb_control_request_t const* req) {
  if (req->bmRequestType_bit.type == TUSB_REQ_TYPE_CLASS) return class_request(rhport, stage, req);

  if (req->bmRequestType_bit.type != TUSB_REQ_TYPE_STANDARD) return false;
  if (req->bmRequestType_bit.recipient != TUSB_REQ_RCPT_INTERFACE) return false;

  const uint8_t itf = tu_u16_low(req->wIndex);
  if (req->bRequest == TUSB_REQ_SET_INTERFACE) {
    if (stage != CONTROL_STAGE_SETUP) return true;
    if (itf == s_itf_as) set_alt(rhport, (uint8_t)req->wValue);
    return tud_control_status(rhport, req);
  }
  if (req->bRequest == TUSB_REQ_GET_INTERFACE) {
    if (stage != CONTROL_STAGE_SETUP) return true;
    s_ctrl_buf[0] = (itf == s_itf_as) ? s_alt : 0;
    return tud_control_xfer(rhport, req, s_ctrl_buf, 1);
  }
  return false;
}

static bool uac_xfer_cb(uint8_t rhport, uint8_t ep_addr, xfer_result_t result, uint32_t xferred_bytes) {
  if (ep_addr != s_ep_out) return false;

  uint32_t len = xferred_bytes & ~3u;
  if (result == XFER_RESULT_SUCCESS && len > 0 && s_alt != 0 && s_cb != NULL) {
    if (s_gain_q15 != 32768) {
      int16_t* s = (int16_t*)s_rx_buf;
      for (uint32_t i = 0; i < len / 2; i++) s[i] = (int16_t)((s[i] * s_gain_q15) >> 15);
    }
    s_cb(s_rx_buf, len);
  }
  arm_rx(rhport);
  return true;
}

static const usbd_class_driver_t s_driver = {
#if CFG_TUSB_DEBUG >= CFG_TUD_LOG_LEVEL
    .name = "UAC1",
#endif
    .init = uac_init,
    .reset = uac_reset,
    .open = uac_open,
    .control_xfer_cb = uac_control_xfer_cb,
    .xfer_cb = uac_xfer_cb,
    .sof = NULL,
};

usbd_class_driver_t const* usbd_app_driver_get_cb(uint8_t* driver_count) {
  *driver_count = 1;
  return &s_driver;
}

bool usb_speaker_begin(usb_speaker_pcm_cb_t cb) {
  s_cb = cb;
  return tinyusb_enable_interface(USB_INTERFACE_CUSTOM, DESC_LEN, descriptor_cb) == ESP_OK;
}

bool usb_speaker_streaming() {
  return s_alt != 0;
}

int16_t usb_speaker_volume() {
  return s_volume;
}

bool usb_speaker_muted() {
  return s_mute;
}
