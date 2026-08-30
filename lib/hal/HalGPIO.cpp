#include "HalGPIO.h"

#include <driver/gpio.h>
#include <esp_sleep.h>

namespace {
// Button wiring: A -> D6, B -> D7, switch to GND.
constexpr int BTN_PINS[HalGPIO::BTN_COUNT] = {D6, D7};
}  // namespace

// A real press holds the pin low for tens of ms at minimum — even the
// fastest deliberate tap comfortably clears this — while an electrical
// glitch (e.g. the e-ink panel's higher-voltage waveform during a full
// refresh coupling into the button line) pulls the line low only briefly.
// A single instantaneous level check at ISR-dispatch time isn't enough to
// tell those apart (a glitch lasting longer than the ISR's few-µs dispatch
// latency, e.g. from a sustained voltage droop rather than a spike, would
// still read low) — so instead this measures how long the line was
// actually held low, between the FALLING and its matching RISING edge, and
// only counts it as a latch if that span clears MIN_PRESS_MS.
static constexpr uint32_t MIN_PRESS_MS = 15;

void IRAM_ATTR HalGPIO::handleIsr(void* arg) {
  auto* b = static_cast<ButtonState*>(arg);
  uint32_t now = millis();
  // gpio_get_level, not digitalRead — this must stay flash-cache-safe since
  // it can fire mid flash write.
  if (gpio_get_level((gpio_num_t)b->pin) == 0) {
    // Falling edge: just remember when. Re-arms on every fall, including
    // bounce during the press itself, so only the last fall before the
    // press actually settles ends up paired with the real release below.
    b->isrFallMs = now;
    b->isrPendingFall = true;
    return;
  }
  // Rising edge with no fall on record (a stray glitch on an already-high
  // line, or the tail of bounce already resolved elsewhere) — nothing to
  // measure against.
  if (!b->isrPendingFall) return;
  b->isrPendingFall = false;
  // Basic ISR-side debounce (below) against double-counting the same
  // press; the poll loop does the authoritative one.
  if (now - b->isrFallMs >= MIN_PRESS_MS && now - b->isrLatchMs >= DEBOUNCE_MS) {
    if (b->isrLatchCount < 255) b->isrLatchCount++;
    b->isrLatchMs = now;
  }
}

void HalGPIO::begin() {
  for (uint8_t i = 0; i < BTN_COUNT; i++) {
    buttons[i].pin = BTN_PINS[i];
    pinMode(buttons[i].pin, INPUT_PULLUP);
    attachInterruptArg(buttons[i].pin, handleIsr, &buttons[i], CHANGE);
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
        // Release seen by polling: this same press was already tracked
        // above (pressedAtMs/stable), so any latches the ISR counted during
        // the hold are re-presses that happened before polling caught the
        // release, not new distinct clicks — drop them or they'd replay as
        // phantom clicks once this release is processed.
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
    b.isrFallMs = now;
    b.isrPendingFall = false;
  }
}
