#include "UiListActivity.h"

#include "../components/UITheme.h"

void UiListActivity::loop() {
  int count = rowCount();

  if (gpio.wasShortPressed(HalGPIO::BTN_A) && count > 0) {
    selected = (selected + 1) % count;
    clampScroll();
    requestUpdate();
  }
  if (gpio.wasLongPressed(HalGPIO::BTN_A) && count > 0) {
    selected = 0;
    clampScroll();
    requestUpdate();
  }
  if (gpio.wasShortPressed(HalGPIO::BTN_B) && count > 0) {
    onSelectRow(selected);
  }
  if (gpio.wasLongPressed(HalGPIO::BTN_B)) {
    onBack();
  }
}

int UiListActivity::visibleRows() const {
  return max(1, (UITheme::FOOTER_Y - UITheme::CONTENT_Y) / rowHeight());
}

void UiListActivity::clampScroll() {
  if (selected < scrollOffset) scrollOffset = selected;
  if (selected >= scrollOffset + visibleRows()) {
    scrollOffset = selected - visibleRows() + 1;
  }
}

int UiListActivity::rowY(int index) const {
  return UITheme::CONTENT_Y + (index - scrollOffset) * rowHeight();
}

bool UiListActivity::rowVisible(int index) const {
  return index >= scrollOffset && index < scrollOffset + visibleRows();
}

void UiListActivity::render() {
  auto& g = display.gfx();
  g.fillScreen(GxEPD_WHITE);
  drawHeader();

  int count = rowCount();
  if (count == 0) {
    auto& t = display.text();
    t.setFont(UITheme::FONT_BODY);
    t.setForegroundColor(GxEPD_BLACK);
    t.setCursor(10, UITheme::CONTENT_Y + 20);
    t.print(emptyText());
  }
  for (int i = scrollOffset; i < count && rowVisible(i); i++) {
    drawRow(i, rowY(i), i == selected);
  }
  UiChrome::drawScrollbar(count, scrollOffset, visibleRows(), rowHeight());
}
