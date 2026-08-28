#include "MainMenuActivity.h"

#include "../../components/Icons.h"
#include "../ActivityManager.h"
#include "../scripts/ScriptRunActivity.h"
#include "../shopping/ShoppingListActivity.h"
#include "../transfer/TransferActivity.h"

void MainMenuActivity::onEnter() {
  Activity::onEnter();
  scripts = SETTINGS.scripts();
}

int MainMenuActivity::cellSize() const {
  return (display.width() - 2 * GRID_MARGIN - (GRID_COLS - 1) * GRID_GAP) / GRID_COLS;
}

void MainMenuActivity::render() {
  auto& g = display.gfx();
  g.fillScreen(GxEPD_WHITE);
  UiChrome::drawHeader();

  int size = cellSize();
  int count = rowCount();
  for (int i = 0; i < count; i++) {
    int y = UITheme::CONTENT_Y + (i / GRID_COLS) * (size + GRID_GAP);
    drawRow(i, y, i == selected);
  }

  int scriptCount = (int)scripts.size();
  const char* label;
  if (selected < scriptCount) {
    label = scripts[selected].label.c_str();
  } else if (SETTINGS.shoppingListEnabled && selected == scriptCount) {
    label = TR(SHOPPING_LIST);
  } else {
    label = TR(TRANSFER);
  }
  UiChrome::drawFooter(label);
}

void MainMenuActivity::drawRow(int index, int y, bool rowSelected) {
  auto& g = display.gfx();
  int size = cellSize();
  int col = index % GRID_COLS;
  int x = GRID_MARGIN + col * (size + GRID_GAP);

  UiChrome::drawRowButton(x, y, size, size, rowSelected, /*thickness=*/2);

  uint16_t fg = rowSelected ? GxEPD_WHITE : GxEPD_BLACK;
  int cx = x + size / 2, cy = y + size / 2;

  int scriptCount = (int)scripts.size();
  if (index < scriptCount) {
    Icons::byKey(g, cx, cy, fg, scripts[index].icon);
  } else if (SETTINGS.shoppingListEnabled && index == scriptCount) {
    Icons::shoppingCart(g, cx, cy, fg);
  } else {
    Icons::wifi(g, cx, cy, fg);
  }
}

void MainMenuActivity::onSelectRow(int index) {
  int scriptCount = (int)scripts.size();
  if (index < scriptCount) {
    activityManager.pushActivity(std::make_unique<ScriptRunActivity>(scripts[index]));
  } else if (SETTINGS.shoppingListEnabled && index == scriptCount) {
    activityManager.pushActivity(std::make_unique<ShoppingListActivity>());
  } else {
    activityManager.pushActivity(std::make_unique<TransferActivity>());
  }
}
