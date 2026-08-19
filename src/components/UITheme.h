#pragma once
#include <U8g2_for_Adafruit_GFX.h>

#include "fonts/NotoSans.h"

// Font roles and layout metrics (CrossPoint UITheme equivalent).
namespace UITheme {

// Fonts (U8g2, baseline-positioned). Noto Sans, custom-converted (_te =
// extended charset with Latin-1 accents for i18n).
inline const uint8_t* FONT_TITLE = u8g2_font_notosans16_te;
inline const uint8_t* FONT_BODY = u8g2_font_notosans14_te;
inline const uint8_t* FONT_SMALL = u8g2_font_notosans10_te;

// Layout (122x250 portrait). No footer — the list gets the full height.
constexpr int HEADER_H = 18;
constexpr int FOOTER_Y = 248;
constexpr int CONTENT_Y = HEADER_H + 2;
constexpr int ROW_H = 26;
constexpr int BTN_RADIUS = 5;

}  // namespace UITheme
