#pragma once
#include <Arduino.h>

#include <vector>

// Home Assistant REST client: runs a script by calling script.turn_on with
// its entity_id (the one service every script entity always exposes), and
// reads/writes a `todo` list entity for the shopping list sync.
class HomeAssistantClient {
 public:
  // One item of a `todo` entity, as returned by todo.get_items.
  struct TodoItem {
    String uid;
    String text;
    bool checked = false;
  };

  // One `todo.*` list entity, as returned by listTodoEntities().
  struct TodoListInfo {
    String entityId;
    String name;
  };

  void begin(const String& host, int port, const String& token);

  // `scriptObjectId` is the part after "script.". Returns true on HTTP
  // 200/201.
  bool runScript(const String& scriptObjectId);

  // Calls todo.get_items (a response-returning service call — needs HA
  // 2024.4+) for `entityId` (full id, e.g. "todo.shopping_list") and parses
  // its items into `outItems`. Returns false — leaving `outItems` untouched —
  // on any HTTP or parse failure.
  bool getTodoItems(const String& entityId, std::vector<TodoItem>& outItems);

  // Calls todo.update_item to set one item's checked state by uid. Returns
  // true on HTTP 200/201.
  bool updateTodoItem(const String& entityId, const String& uid, bool checked);

  // Lists every `todo.*` entity (id + friendly name) via a small Jinja
  // template run through /api/template, rather than pulling the full
  // /api/states dump (every entity's full state+attributes) just to filter
  // one domain client-side — that response can be large enough to strain
  // this device's heap. Returns false — leaving `outLists` untouched — on
  // any HTTP or parse failure.
  bool listTodoEntities(std::vector<TodoListInfo>& outLists);

 private:
  String baseUrl;
  String authHeader;
};
