/*
 * SentencePiece-based tokenizer for Quiet ML.
 */
#include "quiet/ml/tokenizer.h"

#if __has_include("sentencepiece_processor.h")
#include "sentencepiece_processor.h"

namespace Quiet {
namespace Ml {

struct Tokenizer::Impl {
	sentencepiece::SentencePieceProcessor processor;
};

Tokenizer::~Tokenizer() = default;

bool Tokenizer::loadFromFile(const QString &modelPath) {
	if (!_impl) {
		_impl = std::make_unique<Impl>();
	}
	const auto status = _impl->processor.Load(modelPath.toStdString());
	_loaded = status.ok();
	return _loaded;
}

std::vector<int64_t> Tokenizer::encode(const QString &text) const {
	if (!_loaded || !_impl) {
		return {};
	}
	std::vector<int> ids;
	const auto status = _impl->processor.Encode(text.toStdString(), &ids);
	if (!status.ok()) {
		return {};
	}
	return std::vector<int64_t>(ids.begin(), ids.end());
}

QString Tokenizer::decode(const std::vector<int64_t> &ids) const {
	if (!_loaded || !_impl) {
		return {};
	}
	std::vector<int> i(ids.begin(), ids.end());
	std::string out;
	const auto status = _impl->processor.Decode(i, &out);
	if (!status.ok()) {
		return {};
	}
	return QString::fromStdString(out);
}

} // namespace Ml
} // namespace Quiet

#else
// Stub when SentencePiece not available
namespace Quiet {
namespace Ml {

struct Tokenizer::Impl {};

Tokenizer::~Tokenizer() = default;

bool Tokenizer::loadFromFile(const QString &) { return false; }
std::vector<int64_t> Tokenizer::encode(const QString &) const { return {}; }
QString Tokenizer::decode(const std::vector<int64_t> &) const { return {}; }

} // namespace Ml
} // namespace Quiet
#endif
