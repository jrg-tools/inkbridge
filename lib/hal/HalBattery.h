#pragma once
#include <Arduino.h>

// LiPo fuel gauge via ADC. Assumes a 1:2 voltage divider (e.g. 220k/220k)
// from BAT+ to PIN_VBAT on the XIAO ESP32S3. Adjust PIN_VBAT/DIVIDER if
// your wiring differs.
class HalBattery {
 public:
  static constexpr int PIN_VBAT = A0;
  static constexpr float DIVIDER = 2.0f;

  void begin() { pinMode(PIN_VBAT, INPUT); }

  // Battery voltage in millivolts (averaged over a few samples).
  uint32_t millivolts() const {
    uint32_t sum = 0;
    for (int i = 0; i < 4; i++) sum += analogReadMilliVolts(PIN_VBAT);
    return (uint32_t)((sum / 4) * DIVIDER);
  }

  // 0-100, linear map of the useful LiPo range (3.3V empty, 4.2V full).
  int percent() const {
    int32_t mv = millivolts();
    int32_t pct = (mv - 3300) * 100 / (4200 - 3300);
    return constrain(pct, 0, 100);
  }
};

inline HalBattery battery;
