/*
This file is part of Quiet,
a fork of Telegram Desktop for information well-being.

Quiet-specific modifications live in this folder.
*/
#include "quiet/quiet_controller.h"
#include "quiet/quiet_mode_layer_widget.h"

#include "window/window_session_controller.h"

namespace Quiet {

void ShowQuietMode(not_null<Window::SessionController*> controller) {
	controller->showSpecialLayer(
		CreateQuietModeLayer(nullptr, controller),
		anim::type::normal);
}

} // namespace Quiet
