#pragma once
#include <HalBattery.h>
#include <HalDisplay.h>

#include "Icons.h"
#include "UITheme.h"

// Shared screen chrome: battery header and rounded row-buttons.
class UiChrome {
 public:
  // Battery icon + percentage in the top-right corner. No title, no lines.
  static void drawHeader() {
    auto& g = display.gfx();
    auto& t = display.text();

    int pct = battery.percent();
    char buf[8];
    snprintf(buf, sizeof(buf), "%d%%", pct);

    t.setFont(UITheme::FONT_SMALL);
    t.setForegroundColor(GxEPD_BLACK);
    int textW = t.getUTF8Width(buf);
    int x = g.width() - 4 - textW;
    t.setCursor(x, 13);
    t.print(buf);
    Icons::batteryIcon(g, x - 22, 4, pct, GxEPD_BLACK);
  }

  // Row-button: rounded border, inverted (black fill, white text) when
  // selected. Panel is 1-bit — no grey, so selection is a solid black pill.
  static void drawRowButton(int x, int y, int w, int h, bool selected) {
    auto& g = display.gfx();
    if (selected) {
      g.fillRoundRect(x, y, w, h, UITheme::BTN_RADIUS, GxEPD_BLACK);
    } else {
      g.drawRoundRect(x, y, w, h, UITheme::BTN_RADIUS, GxEPD_BLACK);
    }
  }

  // Center-aligned label inside a button box (call after drawRowButton).
  static void drawButtonLabel(int x, int y, int w, int h, const char* label,
                              bool selected) {
    auto& t = display.text();
    t.setFont(UITheme::FONT_BODY);
    t.setForegroundColor(selected ? GxEPD_WHITE : GxEPD_BLACK);
    int textW = t.getUTF8Width(label);
    int baseline = y + (h + t.getFontAscent()) / 2;
    t.setCursor(x + (w - textW) / 2, baseline);
    t.print(label);
  }

  // Right-edge scrollbar for lists longer than the viewport.
  static void drawScrollbar(int total, int offset, int visible, int rowH = UITheme::ROW_H) {
    if (total <= visible) return;
    auto& g = display.gfx();
    int trackY = UITheme::CONTENT_Y;
    int trackH = visible * rowH;
    int x = g.width() - 4;
    g.drawFastVLine(x, trackY, trackH, GxEPD_BLACK);
    int thumbH = max(6, trackH * visible / total);
    int thumbY = trackY + (trackH - thumbH) * offset / max(1, total - visible);
    g.fillRect(x - 1, thumbY, 3, thumbH, GxEPD_BLACK);
  }
};
