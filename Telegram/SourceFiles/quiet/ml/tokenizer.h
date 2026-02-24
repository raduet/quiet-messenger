/*
 * Tokenizer for Quiet ML (SentencePiece wrapper).
 * Load .model file, encode text -> ids, decode ids -> text.
 */
#pragma once

#include <vector>
#include <cstdint>
#include <QString>
#include <memory>

namespace Quiet {
namespace Ml {

class Tokenizer {
public:
	Tokenizer() = default;
	~Tokenizer();

	bool loadFromFile(const QString &modelPath);
	std::vector<int64_t> encode(const QString &text) const;
	QString decode(const std::vector<int64_t> &ids) const;
	bool isLoaded() const { return _loaded; }

private:
	struct Impl;
	std::unique_ptr<Impl> _impl;
	bool _loaded = false;
};

} // namespace Ml
} // namespace Quiet
