#pragma once
#include <memory>
#include <vector>

#include "Activity.h"

// Owns the activity stack and applies transitions deferred, so an activity
// never deletes itself mid-loop() (CrossPoint pattern).
class ActivityManager {
 public:
  // Clears the stack and makes `activity` the only one.
  void replaceActivity(std::unique_ptr<Activity> activity);
  // Pushes on top; previous activity resumes on popActivity().
  void pushActivity(std::unique_ptr<Activity> activity);
  // Returns to the previous activity on the stack.
  void popActivity();

  Activity* getCurrentActivity() { return stack.empty() ? nullptr : stack.back().get(); }

  // Runs current activity loop, applies pending transition, renders if requested.
  void loop();

 private:
  enum class PendingAction { NONE, REPLACE, PUSH, POP };

  void applyPendingAction();

  std::vector<std::unique_ptr<Activity>> stack;
  std::unique_ptr<Activity> pendingActivity;
  PendingAction pendingAction = PendingAction::NONE;
};

extern ActivityManager activityManager;
