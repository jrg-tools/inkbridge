#pragma once
#include <Arduino.h>

// Raw debounced button input, CrossPoint HalGPIO-style.
// Buttons are active-low with internal pull-ups. Call update() once per loop,
// then query the gesture accessors.
//
// Gestures: a press is either SHORT (released before LONG_PRESS_MS) or LONG
// (fires once when the threshold is crossed, while still held) — never both.
// A GPIO interrupt latches press edges so presses aren't lost while the main
// loop is blocked (e-ink refreshes take 0.3-2s).
class HalGPIO {
 public:
  static constexpr uint8_t BTN_A = 0;
  static constexpr uint8_t BTN_B = 1;
  static constexpr uint8_t BTN_COUNT = 2;

  static constexpr uint32_t DEBOUNCE_MS = 20;
  static constexpr uint32_t LONG_PRESS_MS = 600;

  void begin();
  void update();

  bool wasShortPressed(uint8_t btn) const;  // released before LONG_PRESS_MS
  bool wasLongPressed(uint8_t btn) const;   // held past LONG_PRESS_MS (once)
  bool anyEventThisFrame() const;           // any short/long press, either button

  // Arms both button GPIOs as light-sleep wake sources (neither pin is RTC-
  // capable, so deep sleep's ext0/ext1 wakeup can't be used here — light
  // sleep's GPIO wakeup works on any digital pin). Call begin() again after
  // waking to restore the normal FALLING-edge interrupt config.
  void prepareForSleep() const;

  // Discards all debounce/latch state, including any queued isrLatchCount.
  // Call right after waking from sleep: arming the GPIO wakeup source
  // reprograms the same interrupt-type register the normal FALLING-edge
  // ISR uses, so it fires repeatedly (level-triggered) for as long as the
  // waking press is held — without this, that gets replayed as several
  // phantom short-presses once polling resumes. The press that woke the
  // device is consumed for waking only, not treated as input.
  void resetState();

 private:
  struct ButtonState {
    int pin = -1;
    bool stable = false;  // debounced level (true = pressed)
    bool rawLast = false;
    bool longFired = false;
    bool shortEvent = false;
    bool longEvent = false;
    uint32_t lastChangeMs = 0;
    uint32_t pressedAtMs = 0;
    // Press edges latched by ISR while the main loop was blocked. A counter
    // (not a flag) so several clicks during a 2-4s full refresh all replay.
    volatile uint8_t isrLatchCount = 0;
    volatile uint32_t isrLatchMs = 0;
  };
  static void IRAM_ATTR handleIsr(void* arg);
  ButtonState buttons[BTN_COUNT];
};

extern HalGPIO gpio;
