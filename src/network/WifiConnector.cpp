#include "WifiConnector.h"

#include <WiFi.h>

void WifiConnector::begin() {
  networks = SETTINGS.wifis();
  if (networks.empty()) {
    currentStatus = Status::NO_NETWORKS;
    return;
  }
  WiFi.mode(WIFI_STA);
  startAttempt(0);
}

void WifiConnector::startAttempt(size_t idx) {
  index = idx;
  const auto& net = networks[index];
  currentSsid = net.ssid;
  Serial.printf("[Wifi] trying %s (%u/%u)\n", net.ssid.c_str(), (unsigned)(index + 1),
                (unsigned)networks.size());
  WiFi.disconnect();
  WiFi.begin(net.ssid.c_str(), net.password.c_str());
  attemptStartMs = millis();
  currentStatus = Status::CONNECTING;
}

WifiConnector::Status WifiConnector::update() {
  if (currentStatus != Status::CONNECTING) return currentStatus;

  if (WiFi.status() == WL_CONNECTED) {
    currentStatus = Status::CONNECTED;
    return currentStatus;
  }

  if (millis() - attemptStartMs > PER_NETWORK_TIMEOUT_MS) {
    if (index + 1 < networks.size()) {
      startAttempt(index + 1);
    } else {
      Serial.println("[Wifi] all networks failed");
      currentStatus = Status::FAILED;
    }
  }
  return currentStatus;
}
