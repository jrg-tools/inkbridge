#include "HalGPIO.h"

#include <driver/gpio.h>
#include <esp_sleep.h>

namespace {
// Button wiring: A -> D6, B -> D7, switch to GND.
constexpr int BTN_PINS[HalGPIO::BTN_COUNT] = {D6, D7};
}  // namespace

void IRAM_ATTR HalGPIO::handleIsr(void* arg) {
  auto* b = static_cast<ButtonState*>(arg);
  uint32_t now = millis();
  // Basic ISR-side debounce; the poll loop does the authoritative one.
  if (now - b->isrLatchMs >= DEBOUNCE_MS) {
    if (b->isrLatchCount < 255) b->isrLatchCount++;
    b->isrLatchMs = now;
  }
}

void HalGPIO::begin() {
  for (uint8_t i = 0; i < BTN_COUNT; i++) {
    buttons[i].pin = BTN_PINS[i];
    pinMode(buttons[i].pin, INPUT_PULLUP);
    attachInterruptArg(buttons[i].pin, handleIsr, &buttons[i], FALLING);
  }
}

void HalGPIO::update() {
  uint32_t now = millis();
  for (auto& b : buttons) {
    b.shortEvent = false;
    b.longEvent = false;

    bool raw = digitalRead(b.pin) == LOW;
    if (raw != b.rawLast) {
      b.rawLast = raw;
      b.lastChangeMs = now;
    }
    if (now - b.lastChangeMs >= DEBOUNCE_MS && raw != b.stable) {
      b.stable = raw;
      if (raw) {
        b.pressedAtMs = now;
        b.longFired = false;
        // This press edge was also latched by the ISR; consume that latch so
        // it isn't replayed a second time below.
        if (b.isrLatchCount > 0) b.isrLatchCount--;
      } else {
        // Release seen by polling: any latches accumulated during the hold
        // are contact-bounce artifacts (FALLING edges on release), not real
        // presses — drop them or they replay as phantom clicks.
        b.isrLatchCount = 0;
        if (!b.longFired) {
          b.shortEvent = true;  // released before the long-press threshold
        }
      }
    }
    if (b.stable && !b.longFired && now - b.pressedAtMs >= LONG_PRESS_MS) {
      b.longFired = true;
      b.longEvent = true;
    }

    // Replay presses that happened entirely while the loop was blocked
    // (e.g. during an e-ink refresh): the ISR latched the press edges but
    // the button is already released, so polling never saw them. Replay one
    // per update() pass so each becomes a distinct short-press event.
    if (b.isrLatchCount > 0 && !b.stable && !raw) {
      b.isrLatchCount--;
      b.shortEvent = true;
    }
    // If it's still held, polling above picks it up on the following updates.
  }
}

bool HalGPIO::wasShortPressed(uint8_t btn) const { return buttons[btn].shortEvent; }

bool HalGPIO::wasLongPressed(uint8_t btn) const { return buttons[btn].longEvent; }

bool HalGPIO::anyEventThisFrame() const {
  for (const auto& b : buttons) {
    if (b.shortEvent || b.longEvent) return true;
  }
  return false;
}

void HalGPIO::prepareForSleep() const {
  for (const auto& b : buttons) {
    gpio_wakeup_enable((gpio_num_t)b.pin, GPIO_INTR_LOW_LEVEL);
  }
  esp_sleep_enable_gpio_wakeup();
}

void HalGPIO::resetState() {
  uint32_t now = millis();
  for (auto& b : buttons) {
    b.stable = false;
    b.rawLast = false;
    b.longFired = false;
    b.shortEvent = false;
    b.longEvent = false;
    b.lastChangeMs = now;
    b.pressedAtMs = 0;
    b.isrLatchCount = 0;
    b.isrLatchMs = now;
  }
}
