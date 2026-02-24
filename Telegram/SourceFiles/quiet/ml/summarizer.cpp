/*
 * ONNX-based summarizer for Quiet ML.
 * Requires tokenizer for encode/decode; model input: token ids, output: logits or ids.
 */
#include "quiet/ml/summarizer.h"
#include <QStringList>

namespace Quiet {
namespace Ml {

struct Summarizer::Impl {
	// Ort::Env, Ort::Session, and optional Tokenizer ref when integrated
};

Summarizer::~Summarizer() = default;

bool Summarizer::loadModel(const QString &onnxPath) {
	(void)onnxPath;
	// TODO: Ort::Session from onnxPath
	return false;
}

QString Summarizer::summarize(const std::vector<Digest::RawMessage> &messages) const {
	if (!_loaded || messages.empty()) {
		return {};
	}
	QStringList texts;
	for (const auto &m : messages) {
		if (!m.text.isEmpty()) {
			texts.append(m.text);
		}
	}
	// TODO: tokenize concatenated text -> run ONNX -> decode output
	(void)texts;
	return {};
}

} // namespace Ml
} // namespace Quiet
