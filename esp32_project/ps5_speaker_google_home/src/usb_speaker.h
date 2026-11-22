#pragma once

#include <stddef.h>
#include <stdint.h>

// pcm: 48 kHz, 스테레오, 16 bit little-endian. USB 태스크에서 불리므로 오래 붙잡지 말 것.
typedef void (*usb_speaker_pcm_cb_t)(const uint8_t* pcm, size_t len);

// USB.begin() 보다 먼저 불러야 한다.
bool usb_speaker_begin(usb_speaker_pcm_cb_t cb);

bool usb_speaker_streaming();

// 호스트가 정한 음량 (1/256 dB 단위, 0 = 최대) 과 음소거 상태
int16_t usb_speaker_volume();
bool usb_speaker_muted();
