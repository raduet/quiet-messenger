/*
 * Summarizer: run ONNX model to produce 2–3 sentence summary from message list.
 */
#pragma once

#include "quiet/digest/digest_types.h"
#include <QString>
#include <memory>

namespace Quiet {
namespace Ml {

class Summarizer {
public:
	Summarizer() = default;
	~Summarizer();

	bool loadModel(const QString &onnxPath);
	QString summarize(const std::vector<Digest::RawMessage> &messages) const;
	bool isLoaded() const { return _loaded; }

private:
	struct Impl;
	std::unique_ptr<Impl> _impl;
	bool _loaded = false;
};

} // namespace Ml
} // namespace Quiet
