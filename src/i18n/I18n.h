#pragma once
#include <Arduino.h>

// Lightweight i18n, CrossPoint-style: a singleton keyed by enum, with one
// compile-time string table per language. Language persists via SETTINGS.
// Usage: TR(SETUP_HOTSPOT)

enum class Lang : uint8_t { EN = 0, ES = 1, COUNT };

enum class StrId : uint8_t {
  TRANSFER = 0,
  SETUP_HOTSPOT,
  CONNECT_WIFI,
  NO_WIFI_CONFIGURED,
  CONNECTING,
  WIFI_FAILED,
  NOTHING_HERE,
  PASSWORD,
  SEND_FAILED,
  SHOPPING_LIST,
  SYNC_FAILED_HINT,
  COUNT,
};

class I18n {
 public:
  static I18n& getInstance() {
    static I18n instance;
    return instance;
  }

  void setLanguage(Lang l) { lang = l; }

  const char* get(StrId id) const {
    return TABLE[(int)lang][(int)id];
  }

 private:
  I18n() = default;
  Lang lang = Lang::EN;

  static constexpr const char* TABLE[(int)Lang::COUNT][(int)StrId::COUNT] = {
      // EN
      {
          "Transfer",
          "Setup hotspot",
          "Connect WiFi",
          "No WiFi - run setup",
          "Connecting to",
          "Could not connect",
          "Nothing here",
          "Pass:",
          "Could not send",
          "Shopping list",
          "Not synced",
      },
      // ES
      {
          "Transferir",
          "Punto de acceso",
          "Conectar WiFi",
          "Sin WiFi - configura",
          "Conectando a",
          "No se pudo conectar",
          "Nada aquí",
          "Clave:",
          "No se pudo enviar",
          "Lista de compras",
          "Sin sincronizar",
      },
  };
};

#define TR(id) (I18n::getInstance().get(StrId::id))
