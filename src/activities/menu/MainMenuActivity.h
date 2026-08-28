#pragma once
#include <vector>

#include "../../InkBridgeSettings.h"
#include "../UiListActivity.h"

// Root menu: a 2-column grid of square, icon-only buttons — each configured
// HA script (web config's Scripts list), followed by Transfer (WiFi/HA
// connectivity). Device settings (language, hotspot) live in the web
// config UI only.
class MainMenuActivity : public UiListActivity {
 public:
  MainMenuActivity() : UiListActivity("MainMenu") {}

  void onEnter() override;
  void render() override;

 protected:
  int rowCount() const override { return (int)scripts.size() + 1; }
  void drawRow(int index, int y, bool selected) override;
  void onSelectRow(int index) override;
  // Root screen — nothing to go back to.
  void onBack() override {}

 private:
  static constexpr int GRID_COLS = 2;
  static constexpr int GRID_MARGIN = 4;
  static constexpr int GRID_GAP = 4;

  // Square cell size: half the screen width, minus margin/gap.
  int cellSize() const;

  std::vector<InkBridgeSettings::ScriptButton> scripts;
};
