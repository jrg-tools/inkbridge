#pragma once
#include <Arduino.h>

#include "HalDisplay.h"

// One screen = one Activity (CrossPoint pattern). Lifecycle:
//   onEnter() -> loop() [+ render() when an update was requested] -> onExit()
// Activities never destroy themselves directly; they ask the ActivityManager
// for a transition, which is applied after loop() returns.
class Activity {
 public:
  explicit Activity(const char* name) : name(name) {}
  virtual ~Activity() = default;

  virtual void onEnter() { Serial.printf("[Activity] enter %s\n", name); }
  virtual void onExit() { Serial.printf("[Activity] exit %s\n", name); }

  // Per-frame input handling and logic. Runs on the main task.
  virtual void loop() {}

  // Draws one frame. Called between display pages; must be idempotent.
  virtual void render() {}

  // Schedules a render after the current loop() pass.
  void requestUpdate(HalDisplay::RefreshMode mode = HalDisplay::FAST_REFRESH) {
    updateRequested = true;
    if (mode == HalDisplay::FULL_REFRESH) fullRefreshRequested = true;
  }

 protected:
  const char* name;

 private:
  friend class ActivityManager;
  bool updateRequested = false;
  bool fullRefreshRequested = false;
};
