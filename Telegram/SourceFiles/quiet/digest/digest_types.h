/*
 * Quiet digest data types. Contract between data provider, ML pipeline, and UI.
 */
#pragma once

#include <cstdint>
#include <vector>
#include <QString>

namespace Quiet {
namespace Digest {

struct RawMessage {
	uint64_t peerId = 0;
	int32_t msgId = 0;
	int32_t date = 0;
	QString text;
	uint64_t fromId = 0;
	bool out = false;
};

struct ChatMeta {
	uint64_t peerId = 0;
	QString name;
	enum class Type { User, Chat, Channel };
	Type type = Type::User;
};

enum class BranchId : uint8_t {
	Work,
	Family,
	World,
	Projects,
	Life,
	Count
};

struct Branch {
	BranchId id = BranchId::Work;
	QString label;
	std::vector<RawMessage> messages;
};

struct Cluster {
	int id = 0;
	QString summary;
	std::vector<RawMessage> messages;
};

struct TreeSnapshot {
	std::vector<Branch> branches;
	// Per-branch clusters (branch index -> clusters)
	std::vector<std::vector<Cluster>> branchClusters;
};

} // namespace Digest
} // namespace Quiet
