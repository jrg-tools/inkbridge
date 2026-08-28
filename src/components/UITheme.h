#pragma once
#include <U8g2_for_Adafruit_GFX.h>

#include "fonts/NotoSans.h"

// Stock u8g2 fonts (bundled with U8g2_for_Adafruit_GFX, no extra flash for
// new font data). Only the "_te" (extended Latin, accents) cuts are safe
// substitutes for NotoSans — matches the charset i18n needs (á/é/í/ó/ú/ñ).
extern const uint8_t u8g2_font_helvR10_te[];
extern const uint8_t u8g2_font_helvR14_te[];
extern const uint8_t u8g2_font_helvR18_te[];
extern const uint8_t u8g2_font_luRS10_te[];
extern const uint8_t u8g2_font_luRS18_te[];
extern const uint8_t u8g2_font_ncenR10_te[];
extern const uint8_t u8g2_font_ncenR14_te[];
extern const uint8_t u8g2_font_ncenR18_te[];

// Font roles and layout metrics (CrossPoint UITheme equivalent).
namespace UITheme {

// Fonts (U8g2, baseline-positioned). Default is Noto Sans, custom-converted
// (_te = extended charset with Latin-1 accents for i18n). Mutable at
// runtime — see applyFontFamily() — so the web-configured font family
// takes effect without a firmware rebuild.
inline const uint8_t* FONT_TITLE = u8g2_font_notosans16_te;
inline const uint8_t* FONT_BODY = u8g2_font_notosans14_te;
inline const uint8_t* FONT_SMALL = u8g2_font_notosans10_te;

// Swaps all three font roles to the chosen family. Unknown/empty falls back
// to the default ("notosans"). Call once at boot, before the first render —
// the device restarts after a settings save, so no need to re-apply live.
inline void applyFontFamily(const String& family) {
  if (family == "helvetica") {
    FONT_TITLE = u8g2_font_helvR18_te;
    FONT_BODY = u8g2_font_helvR14_te;
    FONT_SMALL = u8g2_font_helvR10_te;
  } else if (family == "lucida") {
    FONT_TITLE = u8g2_font_luRS18_te;
    // Lucida Sans (Bigelow & Holmes) is drawn with deliberately thick,
    // chunky strokes at every cut — designed for on-screen legibility, not
    // to match Helvetica/Noto's weight. Sizing FONT_BODY down to the same
    // nominal size as FONT_SMALL keeps row-button labels from dominating;
    // it'll still read heavier than the other families, since that's the
    // typeface itself, not a scaling issue.
    FONT_BODY = u8g2_font_luRS10_te;
    FONT_SMALL = u8g2_font_luRS10_te;
  } else if (family == "schoolbook") {
    FONT_TITLE = u8g2_font_ncenR18_te;
    FONT_BODY = u8g2_font_ncenR14_te;
    FONT_SMALL = u8g2_font_ncenR10_te;
  } else {
    FONT_TITLE = u8g2_font_notosans16_te;
    FONT_BODY = u8g2_font_notosans14_te;
    FONT_SMALL = u8g2_font_notosans10_te;
  }
}

// Layout (122x250 portrait).
constexpr int HEADER_H = 18;
constexpr int FOOTER_H = 20;
constexpr int FOOTER_Y = 250 - FOOTER_H;  // top of the button-hint footer bar
constexpr int CONTENT_Y = HEADER_H + 8;
constexpr int ROW_H = 26;
constexpr int BTN_RADIUS = 5;

}  // namespace UITheme
