#pragma once
#include <GxEPD2_BW.h>
#include <U8g2_for_Adafruit_GFX.h>

#include <functional>

// Thin HAL over the Waveshare 2.13" V4 panel (GxEPD2), CrossPoint-style.
// Owns the refresh policy: FAST (partial) refreshes with a periodic FULL
// refresh every FULL_REFRESH_INTERVAL frames to clear ghosting.
class HalDisplay {
 public:
  enum RefreshMode {
    FULL_REFRESH,  // full waveform, clears ghosting (~2s)
    FAST_REFRESH,  // partial refresh (~300ms)
  };

  // Pages between forced full refreshes (CrossPoint default cadence).
  static constexpr int FULL_REFRESH_INTERVAL = 15;

  // Wiring per README (XIAO ESP32-S3 <-> Waveshare HAT V4)
  static constexpr int PIN_CS = D1;
  static constexpr int PIN_DC = D2;
  static constexpr int PIN_RST = D3;
  static constexpr int PIN_BUSY = D4;

  HalDisplay();

  void begin();

  // Drawing surface (Adafruit_GFX primitives).
  GxEPD2_BW<GxEPD2_213_B74, GxEPD2_213_B74::HEIGHT>& gfx() { return epd; }

  // U8g2 text renderer bound to gfx() — proper fonts, baseline positioning.
  // The wrapper re-asserts transparent mode: u8g2_SetFont() silently resets
  // is_transparent=0, which draws glyph cells as solid bg_color boxes.
  class TextRenderer : public U8G2_FOR_ADAFRUIT_GFX {
   public:
    void setFont(const uint8_t* font) {
      U8G2_FOR_ADAFRUIT_GFX::setFont(font);
      setFontMode(1);
    }
  };

  TextRenderer& text() { return u8f; }

  int width() { return epd.width(); }

  // Runs drawFrame for each display page and refreshes. FAST_REFRESH is
  // silently promoted to FULL_REFRESH on cadence.
  void refresh(const std::function<void()>& drawFrame, RefreshMode mode = FAST_REFRESH);

  // Fast partial refresh limited to a region (e.g. a single list row).
  // drawFrame still draws the whole frame; only the region is transferred.
  void refreshRegion(int x, int y, int w, int h, const std::function<void()>& drawFrame);

 private:
  GxEPD2_BW<GxEPD2_213_B74, GxEPD2_213_B74::HEIGHT> epd;
  TextRenderer u8f;
  int fastRefreshCount = 0;
};

extern HalDisplay display;
