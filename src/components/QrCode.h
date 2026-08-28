#pragma once
#include <Adafruit_GFX.h>
#include <qrcode.h>

// Draws `payload` as a QR code centered horizontally at (top); returns its
// pixel size. Version 4 (3px modules) fits short payloads; longer ones fall
// back to version 8 with 2px modules (98px, still scannable).
inline int drawQrCode(Adafruit_GFX& g, const char* payload, int top, uint16_t color) {
  QRCode qr;
  uint8_t qrData[qrcode_getBufferSize(8)];
  int scale = 3;
  if (qrcode_initText(&qr, qrData, 4, ECC_MEDIUM, payload) != 0) {
    qrcode_initText(&qr, qrData, 8, ECC_MEDIUM, payload);
    scale = 2;
  }

  int size = qr.size * scale;
  int x0 = (g.width() - size) / 2;
  for (int y = 0; y < qr.size; y++) {
    for (int x = 0; x < qr.size; x++) {
      if (qrcode_getModule(&qr, x, y)) {
        g.fillRect(x0 + x * scale, top + y * scale, scale, scale, color);
      }
    }
  }
  return size;
}
