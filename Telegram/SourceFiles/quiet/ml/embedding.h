/*
 * Placeholder: text -> vector for clustering / semantic grouping.
 * Future: TF-IDF or small ONNX embedding model.
 */
#pragma once

#include <QString>
#include <vector>

namespace Quiet {
namespace Ml {

std::vector<float> EmbedText(const QString &text);
// Batch variant for efficiency
std::vector<std::vector<float>> EmbedTexts(const std::vector<QString> &texts);

} // namespace Ml
} // namespace Quiet
