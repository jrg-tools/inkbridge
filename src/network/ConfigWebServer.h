#pragma once
#include <WebServer.h>

#include <memory>

// API-first config server (CrossPoint-style):
//   GET  /api/status    {"version","ip","mode","rssi","freeHeap","uptime"}
//   GET  /api/settings  current settings JSON (secrets omitted)
//   POST /api/settings  JSON body, applies + persists via SETTINGS
//   POST /api/restart   reboots the device
// All other paths are served from the SvelteKit build on LittleFS (web/,
// deployed with `pnpm deploy` + `pio run -t uploadfs`).
// CORS is enabled so external clients can use the API directly.
class ConfigWebServer {
 public:
  void begin(bool apMode);
  void stop();
  void loop();
  bool isRunning() const { return server != nullptr; }

 private:
  bool serveFile(String path);
  void handleStatus();
  void handleGetSettings();
  void handlePostSettings();
  void handleRestart();
  void handleNotFound();

  std::unique_ptr<WebServer> server;
  bool apMode = false;
};
