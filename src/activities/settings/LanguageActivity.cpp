#include "LanguageActivity.h"

#include "../../InkBridgeSettings.h"
#include "../../i18n/I18n.h"
#include "../ActivityManager.h"

namespace {
struct LangOption {
  Lang lang;
  const char* code;
  const char* label;  // endonym — never translated
};

const LangOption LANGS[] = {
    {Lang::EN, "en", "English"},
    {Lang::ES, "es", "Español"},
};
constexpr int LANG_COUNT = sizeof(LANGS) / sizeof(LANGS[0]);
}  // namespace

int LanguageActivity::rowCount() const { return LANG_COUNT; }

void LanguageActivity::drawRow(int index, int y, bool rowSelected) {
  int x = 4, w = display.width() - 12, h = rowHeight() - 3;
  UiChrome::drawRowButton(x, y, w, h, rowSelected);

  // Endonym label, centered; active language marked with a dot.
  const auto& opt = LANGS[index];
  bool active = I18n::getInstance().language() == opt.lang;
  UiChrome::drawButtonLabel(x, y, w, h, opt.label, rowSelected);
  if (active) {
    auto& g = display.gfx();
    g.fillCircle(x + w - 12, y + h / 2, 3,
                 rowSelected ? GxEPD_WHITE : GxEPD_BLACK);
  }
}

void LanguageActivity::onSelectRow(int index) {
  const auto& opt = LANGS[index];
  I18n::getInstance().setLanguage(opt.lang);
  SETTINGS.language = opt.code;
  SETTINGS.save();
  requestUpdate();
}

void LanguageActivity::onBack() { activityManager.popActivity(); }
