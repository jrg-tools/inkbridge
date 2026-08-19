#pragma once
#include "../../network/ConfigWebServer.h"
#include "../Activity.h"

// Setup mode: opens the "inkbridge-setup" access point and serves the config
// form. The web server persists settings and restarts the device on save.
class SetupApActivity : public Activity {
 public:
  SetupApActivity() : Activity("SetupAp") {}

  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render() override;

 private:
  ConfigWebServer webServer;
  String apIp;
  String apPassword;
};
