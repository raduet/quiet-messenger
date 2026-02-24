/*
This file is part of Quiet,
a fork of Telegram Desktop for information well-being.
*/
#include "quiet/quiet_mode_layer_widget.h"

#include "window/window_session_controller.h"
#include "ui/layers/layer_widget.h"
#include "ui/effects/animations.h"
#include "ui/painter.h"

namespace Quiet {
namespace {

constexpr crl::time kFadeDuration = 400;

class QuietModeLayerWidget final : public Ui::LayerWidget {
public:
	QuietModeLayerWidget(
		QWidget *parent,
		not_null<Window::SessionController*> controller);

	void parentResized() override;
	void showFinished() override;

	bool closeByOutsideClick() const override {
		return true;
	}

protected:
	void paintEvent(QPaintEvent *e) override;
	void keyPressEvent(QKeyEvent *e) override;
	void mousePressEvent(QMouseEvent *e) override;

	void closeHook() override;

private:
	void fadeIn();
	void fadeOut();
	void onFadeOutDone();

	const not_null<Window::SessionController*> _controller;
	Ui::Animations::Simple _opacity;
	bool _hiding = false;
};

QuietModeLayerWidget::QuietModeLayerWidget(
	QWidget *parent,
	not_null<Window::SessionController*> controller)
: LayerWidget(parent)
, _controller(controller) {
	setAttribute(Qt::WA_TransparentForMouseEvents, false);
	_opacity.start([=] { update(); }, 0., 0., 0);
}

void QuietModeLayerWidget::parentResized() {
	const auto parent = parentWidget();
	if (parent) {
		setGeometry(0, 0, parent->width(), parent->height());
	}
}

void QuietModeLayerWidget::showFinished() {
	fadeIn();
}

void QuietModeLayerWidget::fadeIn() {
	_opacity.start([=] { update(); }, 0., 1., kFadeDuration);
}

void QuietModeLayerWidget::closeHook() {
	if (_hiding) return;
	_hiding = true;
	fadeOut();
}

void QuietModeLayerWidget::fadeOut() {
	_opacity.start([=] {
		update();
		if (!_opacity.animating()) {
			onFadeOutDone();
		}
	}, 1., 0., kFadeDuration);
}

void QuietModeLayerWidget::onFadeOutDone() {
	closeLayer();
}

void QuietModeLayerWidget::paintEvent(QPaintEvent *e) {
	Painter p(this);
	const auto opacity = _opacity.value(_hiding ? 0. : 1.);
	if (opacity <= 0.) return;
	p.setOpacity(opacity);
	p.fillRect(rect(), Qt::black);
}

void QuietModeLayerWidget::keyPressEvent(QKeyEvent *e) {
	if (e->key() == Qt::Key_Escape) {
		setClosing();
	}
}

void QuietModeLayerWidget::mousePressEvent(QMouseEvent *e) {
	if (e->button() == Qt::LeftButton) {
		setClosing();
	}
}

} // namespace

object_ptr<Ui::LayerWidget> CreateQuietModeLayer(
		QWidget *parent,
		not_null<Window::SessionController*> controller) {
	return object_ptr<Ui::LayerWidget>::fromRaw(
		new QuietModeLayerWidget(parent, controller));
}

} // namespace Quiet
