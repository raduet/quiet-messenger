/*
This file is part of Quiet,
a fork of Telegram Desktop for information well-being.
*/
#pragma once

#include "base/object_ptr.h"

namespace Window {
class SessionController;
} // namespace Window

namespace Ui {
class LayerWidget;
} // namespace Ui

namespace Quiet {

[[nodiscard]] object_ptr<Ui::LayerWidget> CreateQuietModeLayer(
	QWidget *parent,
	not_null<Window::SessionController*> controller);

} // namespace Quiet
