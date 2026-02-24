/*
This file is part of Quiet,
a fork of Telegram Desktop for information well-being.
*/
#pragma once

namespace Window {
class SessionController;
} // namespace Window

namespace Ui {
class AbstractButton;
} // namespace Ui

namespace Quiet {

[[nodiscard]] not_null<Ui::AbstractButton*> CreateCoverButton(
	not_null<QWidget*> parent,
	not_null<Window::SessionController*> controller);

constexpr int kCoverButtonHeight = 48;

} // namespace Quiet
