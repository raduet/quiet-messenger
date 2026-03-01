if(NOT ONNX_SOURCE_DIR)
    message(FATAL_ERROR "ONNX_SOURCE_DIR required")
endif()

set(CMAKELISTS "${ONNX_SOURCE_DIR}/cmake/CMakeLists.txt")
set(EXT_DEPS "${ONNX_SOURCE_DIR}/cmake/external/onnxruntime_external_deps.cmake")

if(NOT EXISTS "${CMAKELISTS}" OR NOT EXISTS "${EXT_DEPS}")
    message(FATAL_ERROR "ONNX cmake files not found")
endif()

file(READ "${CMAKELISTS}" CONTENT)
if(CONTENT MATCHES "Force MSVC runtime to MDd for protobuf compatibility")
    message(STATUS "ONNX CMakeLists.txt already has CRT patch")
else()
    string(REPLACE
        "include(external/onnxruntime_external_deps.cmake)"
        "# Force MSVC runtime to MDd for protobuf compatibility (avoid LNK2038/MTd vs MDd)\nif(MSVC)\n  set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreadedDebugDLL CACHE STRING \"\" FORCE)\nendif()\ninclude(external/onnxruntime_external_deps.cmake)"
        CONTENT "${CONTENT}")
    file(WRITE "${CMAKELISTS}" "${CONTENT}")
    message(STATUS "Patched ONNX cmake/CMakeLists.txt: force MDd before external deps")
endif()

file(READ "${EXT_DEPS}" EXT_CONTENT)
if(EXT_CONTENT MATCHES "protobuf_MSVC_STATIC_RUNTIME OFF")
    message(STATUS "ONNX external deps already has protobuf_MSVC_STATIC_RUNTIME=OFF")
else()
    string(REPLACE
        "set(protobuf_BUILD_TESTS OFF CACHE BOOL \"Build protobuf tests\" FORCE)"
        "if(MSVC)\n  set(protobuf_MSVC_STATIC_RUNTIME OFF CACHE BOOL \"Use dynamic CRT\" FORCE)\nendif()\nset(protobuf_BUILD_TESTS OFF CACHE BOOL \"Build protobuf tests\" FORCE)"
        EXT_CONTENT "${EXT_CONTENT}")
    file(WRITE "${EXT_DEPS}" "${EXT_CONTENT}")
    message(STATUS "Patched ONNX external deps: protobuf_MSVC_STATIC_RUNTIME=OFF for MSVC")
endif()
