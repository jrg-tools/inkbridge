#pragma once
#include "../../network/ConfigWebServer.h"
#include "../../network/WifiConnector.h"
#include "../Activity.h"

// Joins the saved WiFi network (trying each configured one in order) and
// serves the config web app on it. No on-device controls — just connect,
// then show how to reach the server.
//   B long: back (also while connecting)
class ConnectWifiActivity : public Activity {
 public:
  ConnectWifiActivity() : Activity("ConnectWifi") {}

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render() override;

 private:
  enum class State { NO_WIFI, CONNECTING, CONNECTED, FAILED };

  ConfigWebServer webServer;
  WifiConnector connector;
  State state = State::NO_WIFI;
  String ip;
};
