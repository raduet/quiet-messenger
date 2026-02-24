/*
 * Stub to pull in ONNX Runtime for Quiet ML (summarization, etc.).
 * Only this file and future quiet/ml code depend on ONNX; the rest of the app does not.
 */
#include "onnxruntime/core/session/onnxruntime_c_api.h"

namespace Quiet {
namespace Onnx {

// Ensures the linker keeps onnxruntime; used when Quiet ONNX is enabled.
const OrtApi *GetOrtApi() {
	return OrtGetApiBase()->GetApi(ORT_API_VERSION);
}

} // namespace Onnx
} // namespace Quiet
