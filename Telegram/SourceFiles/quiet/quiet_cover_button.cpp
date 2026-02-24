/*
This file is part of Quiet,
a fork of Telegram Desktop for information well-being.
*/
#include "quiet/quiet_cover_button.h"

#include "quiet/quiet_controller.h"
#include "window/window_session_controller.h"
#include "ui/abstract_button.h"
#include "ui/painter.h"
#include "lang/lang_keys.h"
#include "styles/style_window.h"

#include <QtGui/QImage>

namespace Quiet {
namespace {

constexpr int kGapBetweenLabelAndIcon = 8;

class CoverButton final : public Ui::AbstractButton {
public:
	CoverButton(
		QWidget *parent,
		not_null<Window::SessionController*> controller);

protected:
	void paintEvent(QPaintEvent *e) override;

private:
	const not_null<Window::SessionController*> _controller;
	QImage _icon;
	QString _label;

};

CoverButton::CoverButton(
	QWidget *parent,
	not_null<Window::SessionController*> controller)
: AbstractButton(parent)
, _controller(controller)
, _label(tr::lng_menu_quiet_mode(tr::now)) {
	_icon = QImage(u":/gui/art/quiet_mode.png"_q);
	setPointerCursor(true);
}

void CoverButton::paintEvent(QPaintEvent *e) {
	Painter p(this);
	const auto over = isOver() || isDown();
	if (over) {
		p.fillRect(rect(), st::windowBgOver);
	}
	constexpr int iconSize = 48;
	p.setFont(st::semiboldFont);
	const auto textWidth = st::semiboldFont->width(_label);
	const auto totalWidth = textWidth + kGapBetweenLabelAndIcon + iconSize;
	const auto left = (width() - totalWidth) / 2;
	const auto textRect = QRect(left, 0, textWidth, height());
	p.setPen(over ? st::windowBoldFgOver->c : st::windowBoldFg->c);
	p.drawText(textRect, Qt::AlignLeft | Qt::AlignVCenter, _label);
	if (!_icon.isNull()) {
		const auto iconLeft = left + textWidth + kGapBetweenLabelAndIcon;
		const auto scaled = _icon.scaled(
			iconSize,
			iconSize,
			Qt::KeepAspectRatio,
			Qt::SmoothTransformation);
		const auto x = iconLeft + (iconSize - scaled.width()) / 2;
		const auto y = (height() - scaled.height()) / 2;
		p.drawImage(x, y, scaled);
	}
}

} // namespace

not_null<Ui::AbstractButton*> CreateCoverButton(
		not_null<QWidget*> parent,
		not_null<Window::SessionController*> controller) {
	const auto button = new CoverButton(parent, controller);
	button->setFixedHeight(kCoverButtonHeight);
	button->setClickedCallback([=] {
		ShowQuietMode(controller);
	});
	return button;
}

} // namespace Quiet
