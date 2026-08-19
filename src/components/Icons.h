#pragma once
#include <Adafruit_GFX.h>

// Vector-drawn icons (GFX primitives — no bitmaps to squint at in hex).
// All icons are drawn centered on (cx, cy) and scale with `s` (half-size).
class Icons {
 public:
  // WiFi arcs + dot; when off, a diagonal slash crosses it.
  static void wifi(Adafruit_GFX& g, int cx, int cy, int s, uint16_t color, bool on) {
    // Arcs open upwards; dot at the bottom center.
    for (int r = s / 3; r <= s; r += s / 3) {
      g.drawCircleHelper(cx, cy + 2, r, 0x1, color);  // top-right quadrant
      g.drawCircleHelper(cx, cy + 2, r, 0x2, color);  // top-left quadrant
    }
    g.fillCircle(cx, cy + 2, 1, color);
    if (!on) {
      g.drawLine(cx - s, cy - s + 2, cx + s, cy + s, color);
      g.drawLine(cx - s + 1, cy - s + 2, cx + s + 1, cy + s, color);
    }
  }

  // Lightbulb: filled when on (with rays), outline when off.
  static void bulb(Adafruit_GFX& g, int cx, int cy, int s, uint16_t color, bool on) {
    if (on) {
      g.fillCircle(cx, cy - 1, s - 2, color);
      // rays
      g.drawLine(cx - s, cy - s, cx - s + 2, cy - s + 2, color);
      g.drawLine(cx + s, cy - s, cx + s - 2, cy - s + 2, color);
      g.drawLine(cx, cy - s - 2, cx, cy - s, color);
    } else {
      g.drawCircle(cx, cy - 1, s - 2, color);
    }
    g.fillRect(cx - 2, cy + s - 4, 4, 3, color);  // base
  }

  // Battery outline with terminal nub and fill proportional to pct (0-100).
  // Drawn from top-left (x, y); 18x10 body + 2px nub.
  static void batteryIcon(Adafruit_GFX& g, int x, int y, int pct, uint16_t color) {
    g.drawRoundRect(x, y, 18, 10, 2, color);
    g.fillRect(x + 18, y + 3, 2, 4, color);  // terminal nub
    int fillW = (14 * pct) / 100;
    if (fillW > 0) g.fillRect(x + 2, y + 2, fillW, 6, color);
  }

  // Rocker switch: rounded outline, knob left (off) or right (on).
  static void toggle(Adafruit_GFX& g, int cx, int cy, int s, uint16_t color, bool on) {
    g.drawRoundRect(cx - s, cy - s / 2, 2 * s, s, s / 2, color);
    int knobX = on ? cx + s / 2 : cx - s / 2;
    if (on) {
      g.fillCircle(knobX, cy, s / 2 - 1, color);
    } else {
      g.drawCircle(knobX, cy, s / 2 - 1, color);
    }
  }
};
