#include "ActivityManager.h"

void ActivityManager::replaceActivity(std::unique_ptr<Activity> activity) {
  pendingActivity = std::move(activity);
  pendingAction = PendingAction::REPLACE;
}

void ActivityManager::pushActivity(std::unique_ptr<Activity> activity) {
  pendingActivity = std::move(activity);
  pendingAction = PendingAction::PUSH;
}

void ActivityManager::popActivity() { pendingAction = PendingAction::POP; }

void ActivityManager::applyPendingAction() {
  if (pendingAction == PendingAction::NONE) return;

  Activity* current = getCurrentActivity();
  if (current) current->onExit();

  switch (pendingAction) {
    case PendingAction::REPLACE:
      stack.clear();
      stack.push_back(std::move(pendingActivity));
      break;
    case PendingAction::PUSH:
      stack.push_back(std::move(pendingActivity));
      break;
    case PendingAction::POP:
      if (!stack.empty()) stack.pop_back();
      break;
    default:
      break;
  }
  pendingAction = PendingAction::NONE;

  if (Activity* next = getCurrentActivity()) {
    next->onEnter();
    // Entering a screen always repaints fully to leave a clean slate.
    next->requestUpdate(HalDisplay::FULL_REFRESH);
  }
}

void ActivityManager::loop() {
  Activity* current = getCurrentActivity();
  if (current) current->loop();

  applyPendingAction();

  current = getCurrentActivity();
  if (current && current->updateRequested) {
    auto mode = current->fullRefreshRequested ? HalDisplay::FULL_REFRESH : HalDisplay::FAST_REFRESH;
    current->updateRequested = false;
    current->fullRefreshRequested = false;
    display.refresh([current] { current->render(); }, mode);
  }
}
