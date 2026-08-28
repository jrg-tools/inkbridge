#include "HomeAssistantClient.h"

#include <ArduinoJson.h>
#include <HTTPClient.h>

void HomeAssistantClient::begin(const String& host, int port, const String& token) {
  // Accept a bare host ("homeassistant.local") or one already carrying a
  // scheme ("https://..."), so a user pasting a full URL doesn't produce a
  // double-scheme "http://https://..." — which HTTPClient parses as host
  // "https" and fails DNS.
  String scheme = "http://";
  String bareHost = host;
  if (bareHost.startsWith("https://")) {
    scheme = "https://";
    bareHost.remove(0, 8);
  } else if (bareHost.startsWith("http://")) {
    bareHost.remove(0, 7);
  }
  // port <= 0 means "use the scheme's default port" (443/80) — e.g. a
  // reverse-proxied HTTPS install with no separate port to speak of.
  baseUrl = scheme + bareHost;
  if (port > 0) baseUrl += String(":") + port;
  authHeader = String("Bearer ") + token;
}

bool HomeAssistantClient::runScript(const String& scriptObjectId) {
  HTTPClient http;
  http.setTimeout(3000);
  http.begin(baseUrl + "/api/services/script/turn_on");
  http.addHeader("Authorization", authHeader);
  http.addHeader("Content-Type", "application/json");

  String entityId = "script." + scriptObjectId;
  int code = http.POST(String("{\"entity_id\":\"") + entityId + "\"}");
  http.end();
  Serial.printf("[HA] run %s -> %d\n", entityId.c_str(), code);
  return code == 200 || code == 201;
}

bool HomeAssistantClient::getTodoItems(const String& entityId, std::vector<TodoItem>& outItems) {
  HTTPClient http;
  http.setTimeout(5000);  // list fetch, not fire-and-forget — a bit more slack than runScript
  http.begin(baseUrl + "/api/services/todo/get_items?return_response=true");
  http.addHeader("Authorization", authHeader);
  http.addHeader("Content-Type", "application/json");

  int code = http.POST(String("{\"entity_id\":\"") + entityId + "\"}");
  if (code != 200 && code != 201) {
    Serial.printf("[HA] get_items %s -> %d\n", entityId.c_str(), code);
    http.end();
    return false;
  }
  String body = http.getString();
  http.end();

  JsonDocument doc;
  if (deserializeJson(doc, body) != DeserializationError::Ok) {
    Serial.println("[HA] get_items: invalid JSON response");
    return false;
  }
  JsonArrayConst items = doc["service_response"][entityId.c_str()]["items"].as<JsonArrayConst>();
  if (items.isNull()) {
    Serial.println("[HA] get_items: no service_response items for entity");
    return false;
  }
  for (JsonObjectConst entry : items) {
    TodoItem item;
    item.uid = entry["uid"] | "";
    item.text = entry["summary"] | "";
    item.checked = String((const char*)(entry["status"] | "")) == "completed";
    if (item.uid.length()) outItems.push_back(item);
  }
  return true;
}

bool HomeAssistantClient::updateTodoItem(const String& entityId, const String& uid, bool checked) {
  HTTPClient http;
  http.setTimeout(3000);
  http.begin(baseUrl + "/api/services/todo/update_item");
  http.addHeader("Authorization", authHeader);
  http.addHeader("Content-Type", "application/json");

  String status = checked ? "completed" : "needs_action";
  String payload = String("{\"entity_id\":\"") + entityId + "\",\"item\":\"" + uid +
                    "\",\"status\":\"" + status + "\"}";
  int code = http.POST(payload);
  http.end();
  Serial.printf("[HA] update_item %s (%s) -> %d\n", uid.c_str(), status.c_str(), code);
  return code == 200 || code == 201;
}
