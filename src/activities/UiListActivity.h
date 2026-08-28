#pragma once
#include <HalGPIO.h>

#include "../components/UiChrome.h"
#include "../i18n/I18n.h"
#include "Activity.h"

// Reusable scrolling-list screen (CrossPoint UiListActivity equivalent).
// Subclasses provide row data/drawing; this class owns selection, wrapping,
// scrolling, the scrollbar, and the A-button navigation:
//   A short: next row (wraps)   A long: previous row (wraps)
//   B short: onSelectRow()      B long: onBack()
class UiListActivity : public Activity {
 public:
  using Activity::Activity;

  void loop() override;
  void render() override;

 protected:
  virtual int rowCount() const = 0;
  // Draw one row at y (row box is rowHeight() tall). Draw the rounded
  // button chrome with UiChrome::drawRowButton(...) for the standard look.
  virtual void drawRow(int index, int y, bool selected) = 0;
  virtual void onSelectRow(int index) {}
  virtual void onBack() {}
  // Empty header by default; override for custom chrome.
  virtual void drawHeader() { UiChrome::drawHeader(); }
  // Shown centered when rowCount() == 0.
  virtual const char* emptyText() const { return TR(NOTHING_HERE); }
  // Row height in pixels; override for taller (e.g. two-line) rows.
  virtual int rowHeight() const { return UITheme::ROW_H; }
  // Centered footer label, passed through to UiChrome::drawFooter(). Default
  // blank; override for a status hint (e.g. ShoppingListActivity's "not
  // synced").
  virtual const char* footerLabel() const { return nullptr; }

  int visibleRows() const;
  int rowY(int index) const;
  bool rowVisible(int index) const;

  int selected = 0;
  int scrollOffset = 0;

 private:
  void clampScroll();
};
