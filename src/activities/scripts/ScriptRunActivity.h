#pragma once
#include "../../InkBridgeSettings.h"
#include "../../homeassistant/HomeAssistantClient.h"
#include "../../network/WifiConnector.h"
#include "../Activity.h"

// Runs one configured HA script: joins WiFi (trying each configured network
// in order), calls script.turn_on with the script's entity_id, then returns
// to the main menu. No on-device controls, no intermediate "connecting" or
// "done" text — just a spinner while it's busy, an error screen if it fails.
//   B long: back (also while connecting)
class ScriptRunActivity : public Activity {
 public:
  explicit ScriptRunActivity(const InkBridgeSettings::ScriptButton& script)
      : Activity("ScriptRun"), script(script) {}

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render() override;

 private:
  enum class State { NO_WIFI, CONNECTING, FAILED };

  static constexpr uint32_t SPINNER_TICK_MS = 400;

  InkBridgeSettings::ScriptButton script;
  HomeAssistantClient haClient;
  WifiConnector connector;
  State state = State::NO_WIFI;
  uint32_t lastSpinnerTickMs = 0;
  int spinnerFrame = 0;
};
