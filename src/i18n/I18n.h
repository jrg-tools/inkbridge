#pragma once
#include <Arduino.h>

// Lightweight i18n, CrossPoint-style: a singleton keyed by enum, with one
// compile-time string table per language. Language persists via SETTINGS.
// Usage: TR(SETUP_HOTSPOT)

enum class Lang : uint8_t { EN = 0, ES = 1, COUNT };

enum class StrId : uint8_t {
  TRANSFER = 0,
  SETTINGS_MENU,
  LANGUAGE,
  SETUP_HOTSPOT,
  CONNECT_WIFI,
  NO_WIFI_CONFIGURED,
  SYNCING_HA,
  WIFI_SEARCHING,
  NOTHING_HERE,
  PASSWORD,
  SYSTEM,
  VERSION,
  BATTERY,
  HOTSPOT,
  COUNT,
};

class I18n {
 public:
  static I18n& getInstance() {
    static I18n instance;
    return instance;
  }

  void setLanguage(Lang l) { lang = l; }
  Lang language() const { return lang; }

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
          "Settings",
          "Language",
          "Setup hotspot",
          "Connect WiFi",
          "No WiFi - run setup",
          "Syncing with HA...",
          "WiFi: searching...",
          "Nothing here",
          "Pass:",
          "System",
          "Version",
          "Battery",
          "Hotspot",
      },
      // ES
      {
          "Transferir",
          "Ajustes",
          "Idioma",
          "Punto de acceso",
          "Conectar WiFi",
          "Sin WiFi - configura",
          "Sincronizando HA...",
          "WiFi: buscando...",
          "Nada aquí",
          "Clave:",
          "Sistema",
          "Versión",
          "Batería",
          "Punto de acceso",
      },
  };
};

#define TR(id) (I18n::getInstance().get(StrId::id))
