#include "HomeAssistantClient.h"

#include <ArduinoJson.h>
#include <HTTPClient.h>

void HomeAssistantClient::begin(const String& host, int port, const String& token) {
  baseUrl = String("http://") + host + ":" + port;
  authHeader = String("Bearer ") + token;
  connected = false;
}

// GET /api/states/<id> per entity — avoids parsing the huge /api/states payload.
bool HomeAssistantClient::fetch(const std::vector<String>& ids, std::vector<Entity>& out) {
  out.clear();
  bool anyOk = false;

  for (const auto& id : ids) {
    HTTPClient http;
    http.setTimeout(3000);
    http.begin(baseUrl + "/api/states/" + id);
    http.addHeader("Authorization", authHeader);

    Entity entity;
    entity.id = id;
    entity.name = id.substring(id.indexOf('.') + 1);
    entity.toggleable = id.startsWith("light.") || id.startsWith("switch.");
    entity.state = "???";

    int code = http.GET();
    if (code == 200) {
      JsonDocument doc;
      if (deserializeJson(doc, http.getStream()) == DeserializationError::Ok) {
        entity.state = doc["state"].as<const char*>();
        const char* friendlyName = doc["attributes"]["friendly_name"];
        if (friendlyName) entity.name = friendlyName;
        anyOk = true;
      }
    } else {
      Serial.printf("[HA] GET %s -> %d\n", id.c_str(), code);
    }
    http.end();
    out.push_back(entity);
  }

  connected = anyOk;
  return anyOk;
}

bool HomeAssistantClient::toggle(const Entity& entity) {
  if (!entity.toggleable) return false;

  String domain = entity.id.substring(0, entity.id.indexOf('.'));
  HTTPClient http;
  http.setTimeout(3000);
  http.begin(baseUrl + "/api/services/" + domain + "/toggle");
  http.addHeader("Authorization", authHeader);
  http.addHeader("Content-Type", "application/json");

  int code = http.POST(String("{\"entity_id\":\"") + entity.id + "\"}");
  http.end();
  Serial.printf("[HA] toggle %s -> %d\n", entity.id.c_str(), code);
  return code == 200 || code == 201;
}
