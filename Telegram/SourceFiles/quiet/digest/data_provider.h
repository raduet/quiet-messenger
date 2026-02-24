/*
 * Collects raw messages and chat metadata from session for the digest pipeline.
 * Implemented in the main app (uses session().data(), history, etc.).
 */
#pragma once

#include "quiet/digest/digest_types.h"
#include <vector>

namespace Main {
class Session;
} // namespace Main

namespace Quiet {
namespace Digest {

std::vector<RawMessage> CollectMessagesForDigest(
	Main::Session *session,
	int maxMessages,
	int maxDaysBack);

std::vector<ChatMeta> CollectChatMeta(Main::Session *session);

} // namespace Digest
} // namespace Quiet
