#include "ConfigWebServer.h"

#include <ArduinoJson.h>
#include <LittleFS.h>
#include <WiFi.h>

#include "../InkBridgeSettings.h"
#include "../Version.h"
#include "../i18n/I18n.h"

namespace {
const char* contentTypeFor(const String& path) {
  if (path.endsWith(".html")) return "text/html";
  if (path.endsWith(".js")) return "application/javascript";
  if (path.endsWith(".css")) return "text/css";
  if (path.endsWith(".svg")) return "image/svg+xml";
  if (path.endsWith(".png")) return "image/png";
  if (path.endsWith(".ico")) return "image/x-icon";
  if (path.endsWith(".json")) return "application/json";
  if (path.endsWith(".txt")) return "text/plain";
  return "application/octet-stream";
}
}  // namespace

void ConfigWebServer::begin(bool ap) {
  apMode = ap;
  if (!LittleFS.begin()) {
    Serial.println("[Web] LittleFS mount failed — run `pio run -t uploadfs`");
  }

  server = std::make_unique<WebServer>(80);
  server->enableCORS(true);

  server->on("/api/status", HTTP_GET, [this] { handleStatus(); });
  server->on("/api/settings", HTTP_GET, [this] { handleGetSettings(); });
  server->on("/api/settings", HTTP_POST, [this] { handlePostSettings(); });
  server->on("/api/restart", HTTP_POST, [this] { handleRestart(); });
  // Everything else falls through to the SvelteKit build on LittleFS.
  server->onNotFound([this] { handleNotFound(); });

  server->begin();
  Serial.println("[Web] config server on port 80");
}

void ConfigWebServer::stop() {
  if (!server) return;
  server->stop();
  server.reset();
  LittleFS.end();
}

void ConfigWebServer::loop() {
  if (server) server->handleClient();
}

bool ConfigWebServer::serveFile(String path) {
  if (path.endsWith("/")) path += "index.html";
  if (!LittleFS.exists(path)) return false;
  File file = LittleFS.open(path, "r");
  if (!file) return false;
  // Immutable hashed assets under /_app/immutable can be cached hard.
  if (path.startsWith("/_app/immutable/")) {
    server->sendHeader("Cache-Control", "public, max-age=31536000, immutable");
  }
  server->streamFile(file, contentTypeFor(path));
  file.close();
  return true;
}

void ConfigWebServer::handleStatus() {
  JsonDocument doc;
  doc["version"] = INKBRIDGE_VERSION;
  doc["ip"] = apMode ? WiFi.softAPIP().toString() : WiFi.localIP().toString();
  doc["mode"] = apMode ? "AP" : "STA";
  doc["rssi"] = apMode ? 0 : WiFi.RSSI();
  doc["freeHeap"] = ESP.getFreeHeap();
  doc["uptime"] = millis() / 1000;

  String response;
  serializeJson(doc, response);
  server->send(200, "application/json", response);
}

void ConfigWebServer::handleGetSettings() {
  // Secrets (wifi/haToken passwords) are never returned.
  // Grouped to mirror the device menus: transfer (connectivity) / settings.
  JsonDocument doc;
  JsonObject transfer = doc["transfer"].to<JsonObject>();
  // SSID only — passwords never leave the device. The web UI merges these
  // back in by SSID on save, so leaving a password field blank keeps it.
  JsonArray wifiArr = transfer["wifiNetworks"].to<JsonArray>();
  for (const auto& net : SETTINGS.wifis()) {
    wifiArr.add<JsonObject>()["ssid"] = net.ssid;
  }
  transfer["haHost"] = SETTINGS.haHost;
  transfer["haPort"] = SETTINGS.haPort;
  transfer["haEntities"] = SETTINGS.haEntities;
  // Sent as a nested array (not a string) so the web UI can bind it directly.
  JsonDocument scriptsDoc;
  deserializeJson(scriptsDoc, SETTINGS.haScripts);
  transfer["haScripts"] = scriptsDoc;
  JsonObject settings = doc["settings"].to<JsonObject>();
  settings["language"] = SETTINGS.language;
  settings["fontFamily"] = SETTINGS.fontFamily;
  // Hotspot credentials are shown on the device screen, so not secret.
  settings["apSsid"] = SETTINGS.apSsid;
  settings["apPassword"] = SETTINGS.apPassword;

  String response;
  serializeJson(doc, response);
  server->send(200, "application/json", response);
}

void ConfigWebServer::handlePostSettings() {
  JsonDocument doc;
  if (deserializeJson(doc, server->arg("plain")) != DeserializationError::Ok) {
    server->send(400, "text/plain", "Invalid JSON");
    return;
  }

  int applied = 0;
  auto applyString = [&](JsonVariantConst src, const char* key, String& target) {
    const char* value = src[key];
    if (value) {
      target = value;
      applied++;
    }
  };
  // Accept both grouped ({transfer:{...},settings:{...}}) and flat payloads.
  JsonVariantConst root = doc.as<JsonVariantConst>();
  JsonVariantConst transfer =
      root["transfer"].is<JsonObjectConst>() ? root["transfer"] : root;
  JsonVariantConst settings =
      root["settings"].is<JsonObjectConst>() ? root["settings"] : root;

  // Posted as a nested array of {ssid, password}. A blank password keeps
  // the previously stored one for that SSID (matched by SSID, since the
  // list is freely reorderable) — same "blank = unchanged" convention as
  // every other secret field here.
  if (transfer["wifiNetworks"].is<JsonArrayConst>()) {
    auto existing = SETTINGS.wifis();
    JsonDocument outDoc;
    JsonArray outArr = outDoc.to<JsonArray>();
    for (JsonObjectConst entry : transfer["wifiNetworks"].as<JsonArrayConst>()) {
      String ssid = entry["ssid"] | "";
      if (!ssid.length()) continue;
      String password = entry["password"] | "";
      if (!password.length()) {
        for (const auto& net : existing) {
          if (net.ssid == ssid) {
            password = net.password;
            break;
          }
        }
      }
      JsonObject o = outArr.add<JsonObject>();
      o["ssid"] = ssid;
      o["password"] = password;
    }
    String out;
    serializeJson(outArr, out);
    SETTINGS.wifiNetworks = out;
    applied++;
  }
  applyString(transfer, "haHost", SETTINGS.haHost);
  applyString(transfer, "haToken", SETTINGS.haToken);
  applyString(transfer, "haEntities", SETTINGS.haEntities);
  if (transfer["haPort"].is<int>()) {
    SETTINGS.haPort = transfer["haPort"].as<int>();
    applied++;
  }
  // Posted as a nested array; re-serialize to the flat string form we store.
  if (transfer["haScripts"].is<JsonArrayConst>()) {
    String out;
    serializeJson(transfer["haScripts"], out);
    SETTINGS.haScripts = out;
    applied++;
  }
  applyString(settings, "language", SETTINGS.language);
  applyString(settings, "fontFamily", SETTINGS.fontFamily);
  applyString(settings, "apSsid", SETTINGS.apSsid);
  // Empty apPassword is allowed: it regenerates on next hotspot start.
  if (settings["apPassword"].is<const char*>()) {
    SETTINGS.apPassword = settings["apPassword"].as<const char*>();
    applied++;
  }
  SETTINGS.save();
  I18n::getInstance().setLanguage(SETTINGS.language == "es" ? Lang::ES : Lang::EN);

  server->send(200, "text/plain", String("Applied ") + applied + " setting(s)");
}

void ConfigWebServer::handleRestart() {
  server->send(200, "text/plain", "Restarting");
  delay(500);
  ESP.restart();
}

void ConfigWebServer::handleNotFound() {
  // Answer CORS preflight; keep /api/* 404s honest so XHR errors surface.
  if (server->method() == HTTP_OPTIONS) {
    server->send(204);
    return;
  }
  if (!server->uri().startsWith("/api/")) {
    if (serveFile(server->uri())) return;
    if (apMode) {
      // Captive-portal style redirect for unknown non-API paths.
      server->sendHeader("Location", "/", true);
      server->send(302, "text/plain", "");
      return;
    }
  }
  server->send(404, "text/plain", "Not found");
}
