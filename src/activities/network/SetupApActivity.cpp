#include "SetupApActivity.h"

#include <ESPmDNS.h>
#include <HalGPIO.h>
#include <WiFi.h>
#include <qrcode.h>

#include "../../InkBridgeSettings.h"
#include "../../components/UiChrome.h"
#include "../../i18n/I18n.h"
#include "../ActivityManager.h"

namespace {
// Random WPA2 password: 8 chars, unambiguous alphanumerics (no 0/O, 1/l/I).
String randomPassword() {
  static const char CHARSET[] = "23456789abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ";
  String pass;
  pass.reserve(8);
  for (int i = 0; i < 8; i++) {
    pass += CHARSET[esp_random() % (sizeof(CHARSET) - 1)];
  }
  return pass;
}

// Draws a WiFi-join QR code centered horizontally at (top), returns its size.
// Standard format: WIFI:T:WPA;S:<ssid>;P:<password>;;
int drawWifiQr(Adafruit_GFX& g, const char* ssid, const String& password, int top) {
  String payload = String("WIFI:T:WPA;S:") + ssid + ";P:" + password + ";;";

  // Version 4 (3px modules) fits short credentials; longer ones fall back to
  // version 8 with 2px modules (98px, still scannable).
  QRCode qr;
  uint8_t qrData[qrcode_getBufferSize(8)];
  int scale = 3;
  if (qrcode_initText(&qr, qrData, 4, ECC_MEDIUM, payload.c_str()) != 0) {
    qrcode_initText(&qr, qrData, 8, ECC_MEDIUM, payload.c_str());
    scale = 2;
  }

  int size = qr.size * scale;
  int x0 = (g.width() - size) / 2;
  for (int y = 0; y < qr.size; y++) {
    for (int x = 0; x < qr.size; x++) {
      if (qrcode_getModule(&qr, x, y)) {
        g.fillRect(x0 + x * scale, top + y * scale, scale, scale, GxEPD_BLACK);
      }
    }
  }
  return size;
}
}  // namespace

void SetupApActivity::onEnter() {
  Activity::onEnter();
  // Password is generated once on the first hotspot start, then persisted.
  // It can be changed (or cleared to regenerate) via the web API.
  if (SETTINGS.apPassword.length() < 8) {
    SETTINGS.apPassword = randomPassword();
    SETTINGS.save();
  }
  apPassword = SETTINGS.apPassword;
  WiFi.mode(WIFI_AP);
  WiFi.softAP(SETTINGS.apSsid.c_str(), apPassword.c_str());
  apIp = WiFi.softAPIP().toString();
  Serial.printf("[AP] %s up, IP %s\n", SETTINGS.apSsid.c_str(), apIp.c_str());
  MDNS.begin("inkbridge");
  webServer.begin(/*apMode=*/true);
}

void SetupApActivity::onExit() {
  webServer.stop();
  MDNS.end();
  WiFi.softAPdisconnect(true);
  WiFi.mode(WIFI_OFF);
  Activity::onExit();
}

void SetupApActivity::loop() {
  webServer.loop();
  // Long-press events only fire for presses that started after the last
  // press edge, so the menu's select press can't leak in here.
  if (gpio.wasLongPressed(HalGPIO::BTN_B)) {
    activityManager.popActivity();
  }
}

void SetupApActivity::render() {
  auto& g = display.gfx();
  auto& t = display.text();
  g.fillScreen(GxEPD_WHITE);
  UiChrome::drawHeader();

  // Centered-line helper: keeps every row inside the 122px width.
  auto centered = [&](const char* text, int baseline) {
    int w = t.getUTF8Width(text);
    t.setCursor((g.width() - w) / 2, baseline);
    t.print(text);
  };

  // Scan-to-join QR right under the header (ends at ~121px for version 4).
  int qrTop = UITheme::CONTENT_Y + 2;
  int qrSize = drawWifiQr(g, SETTINGS.apSsid.c_str(), apPassword, qrTop);

  // Credentials for manual joining, then the config URL — all centered.
  t.setForegroundColor(GxEPD_BLACK);
  int y = qrTop + qrSize + 16;
  t.setFont(UITheme::FONT_BODY);
  centered(SETTINGS.apSsid.c_str(), y);

  y += 20;
  String pass = String(TR(PASSWORD)) + " " + apPassword;
  centered(pass.c_str(), y);

  y += 20;
  t.setFont(UITheme::FONT_SMALL);
  centered("inkbridge.local", y);
  y += 13;
  String ip = "(" + apIp + ")";
  centered(ip.c_str(), y);
}
