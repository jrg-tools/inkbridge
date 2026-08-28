#pragma once
#include <HalDisplay.h>

#include "Icons.h"
#include "UITheme.h"

// Shared screen chrome: header and rounded row-buttons.
class UiChrome {
 public:
  // Screen title in the top-left, bold, with a short rule underneath (just
  // the title's width) so a submenu makes clear which screen it is.
  // Omit/empty for a blank title (e.g. the root menu, which needs no "you
  // are here"). Right side always shows a status icon regardless of title:
  // a lightning bolt when USB is plugged in (native-USB SOF detection —
  // only fires for an actual host like a computer, not a plain power
  // brick with no data lines), else a moon when `idleSleepEligible` (the
  // one screen the idle-sleep timer actually applies to — see main.cpp).
  static void drawHeader(const char* title = nullptr, bool idleSleepEligible = false) {
    auto& g = display.gfx();
    auto& t = display.text();
    t.setFont(UITheme::FONT_SMALL);
    t.setForegroundColor(GxEPD_BLACK);

    if (title && title[0]) {
      int x = 4;
      int textW = t.getUTF8Width(title);
      // Faux-bold: the custom font set has no bold cut, so redraw 1px over.
      t.setCursor(x, 13);
      t.print(title);
      t.setCursor(x + 1, 13);
      t.print(title);
      g.drawFastHLine(x, UITheme::HEADER_H, textW + 1, GxEPD_BLACK);
    }

    int iconCx = g.width() - 9, iconCy = UITheme::HEADER_H / 2;
    if (Serial.isPlugged()) {
      Icons::zapSmall(g, iconCx, iconCy, GxEPD_BLACK);
    } else if (idleSleepEligible) {
      Icons::moonSmall(g, iconCx, iconCy, GxEPD_BLACK);
    }
  }

  // Row-button: rounded border, inverted (black fill, white text) when
  // selected. Panel is 1-bit — no grey, so selection is a solid black pill.
  // `thickness` only affects the unselected outline (selected is already a
  // solid fill); drawn as concentric inset rects since GxEPD2 has no
  // stroke-width option of its own.
  static void drawRowButton(int x, int y, int w, int h, bool selected, int thickness = 1) {
    auto& g = display.gfx();
    if (selected) {
      g.fillRoundRect(x, y, w, h, UITheme::BTN_RADIUS, GxEPD_BLACK);
    } else {
      for (int i = 0; i < thickness; i++) {
        g.drawRoundRect(x + i, y + i, w - 2 * i, h - 2 * i, UITheme::BTN_RADIUS, GxEPD_BLACK);
      }
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

  // Button-hint footer for list screens: bold "A" bottom-left (the action
  // button — select/run/back), up/down chevrons bottom-right (the move
  // button — next/previous row). `label`, when given, is centered between
  // them (the main menu uses this for the currently selected item's name;
  // other screens leave it blank).
  static void drawFooter(const char* label = nullptr) {
    auto& g = display.gfx();
    auto& t = display.text();
    int midY = UITheme::FOOTER_Y + UITheme::FOOTER_H / 2;

    t.setFont(UITheme::FONT_SMALL);
    t.setForegroundColor(GxEPD_BLACK);
    int baseline = midY + t.getFontAscent() / 2;
    // Faux-bold: the custom font set has no bold cut, so redraw 1px over.
    t.setCursor(6, baseline);
    t.print("A");
    t.setCursor(7, baseline);
    t.print("A");

    Icons::upDown(g, g.width() - 10, midY, 4, GxEPD_BLACK);

    if (label && label[0]) {
      int textW = t.getUTF8Width(label);
      t.setCursor((g.width() - textW) / 2, baseline);
      t.print(label);
    }
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
