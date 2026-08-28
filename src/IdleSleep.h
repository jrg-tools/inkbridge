#pragma once
#include <Arduino.h>

// Single source of truth for the idle-sleep threshold and how long since
// the last button press — shared between main.cpp's actual sleep trigger
// and the main menu's header hint (see MainMenuActivity, UiChrome).
namespace IdleSleep {

constexpr uint32_t TIMEOUT_MS = 5 * 60 * 1000;
// The header shows the "about to sleep" moon for this long beforehand,
// rather than for the whole idle period — nothing renders during actual
// sleep, so this window is the closest honest approximation of "sleeping."
constexpr uint32_t WARNING_MS = 30 * 1000;

inline uint32_t lastActivityMs = 0;

inline void noteActivity() { lastActivityMs = millis(); }
inline uint32_t idleMs() { return millis() - lastActivityMs; }
inline bool nearTimeout() { return idleMs() >= TIMEOUT_MS - WARNING_MS; }
inline bool timedOut() { return idleMs() >= TIMEOUT_MS; }

}  // namespace IdleSleep
