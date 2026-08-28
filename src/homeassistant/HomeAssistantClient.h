#pragma once
#include <Arduino.h>

// Home Assistant REST client: runs a script by calling script.turn_on with
// its entity_id, the one service every script entity always exposes.
class HomeAssistantClient {
 public:
  void begin(const String& host, int port, const String& token);

  // `scriptObjectId` is the part after "script.". Returns true on HTTP
  // 200/201.
  bool runScript(const String& scriptObjectId);

 private:
  String baseUrl;
  String authHeader;
};
