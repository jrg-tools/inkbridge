#include "HomeAssistantClient.h"

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
