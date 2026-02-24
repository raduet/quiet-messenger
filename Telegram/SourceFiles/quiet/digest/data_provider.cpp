/*
 * Stub: real implementation will use session().data(), history(peer), message(FullMsgId).
 */
#include "quiet/digest/data_provider.h"

namespace Quiet {
namespace Digest {

std::vector<RawMessage> CollectMessagesForDigest(
		Main::Session *session,
		int maxMessages,
		int maxDaysBack) {
	(void)session;
	(void)maxMessages;
	(void)maxDaysBack;
	return {};
}

std::vector<ChatMeta> CollectChatMeta(Main::Session *session) {
	(void)session;
	return {};
}

} // namespace Digest
} // namespace Quiet
