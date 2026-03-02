#include "quiet/ml/readiness.h"

namespace Quiet {
namespace Ml {

bool IsQuietMlReady() {
#if defined(QUIET_HAVE_SENTENCEPIECE)
	return true;
#else
	return false;
#endif
}

} // namespace Ml
} // namespace Quiet
