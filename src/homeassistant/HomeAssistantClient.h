#pragma once
#include <Arduino.h>

#include <vector>

// Home Assistant REST client (per-entity GET, service toggle).
class HomeAssistantClient {
 public:
  struct Entity {
    String id;        // "light.kitchen"
    String name;      // friendly_name (id suffix fallback)
    String state;     // "on", "off", "22.5", "???"...
    bool toggleable;  // light.* / switch.*
  };

  void begin(const String& host, int port, const String& token);

  // Fetches state for each id. Returns true if at least one succeeded.
  bool fetch(const std::vector<String>& ids, std::vector<Entity>& out);

  // Toggles a light/switch. Returns true on HTTP 200/201.
  bool toggle(const Entity& entity);

  bool isConnected() const { return connected; }

 private:
  String baseUrl;
  String authHeader;
  bool connected = false;
};
