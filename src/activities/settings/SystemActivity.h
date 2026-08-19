#pragma once
#include "../Activity.h"

// System settings/info screen: firmware version, battery, hotspot
// credentials. Values are edited via the web API; this screen displays them.
//   B long: back
class SystemActivity : public Activity {
 public:
  SystemActivity() : Activity("System") {}

  void loop() override;
  void render() override;
};
