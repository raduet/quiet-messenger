/*
 * Placeholder: group message indices by embedding similarity (e.g. K-means).
 * Input: vectors per message, output: cluster id per message.
 */
#pragma once

#include <vector>

namespace Quiet {
namespace Ml {

// Returns cluster id for each input index (0..numClusters-1).
std::vector<int> ClusterByEmbedding(
	const std::vector<std::vector<float>> &embeddings,
	int numClusters);

} // namespace Ml
} // namespace Quiet
