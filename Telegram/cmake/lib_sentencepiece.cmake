# SentencePiece tokenizer (for Quiet ML only).
# Requires: Telegram/ThirdParty/sentencepiece cloned.
# Clone: git clone --depth 1 https://github.com/google/sentencepiece.git Telegram/ThirdParty/sentencepiece

set(QUIET_SENTENCEPIECE_AVAILABLE OFF)

if (NOT EXISTS "${third_party_loc}/sentencepiece/CMakeLists.txt")
    message(WARNING "SentencePiece source not found at ${third_party_loc}/sentencepiece. Quiet tokenizer disabled. Clone: git clone --depth 1 https://github.com/google/sentencepiece.git Telegram/ThirdParty/sentencepiece")
    return()
endif()

# VERSION.txt is required by sentencepiece CMake
if (NOT EXISTS "${third_party_loc}/sentencepiece/VERSION.txt")
    message(WARNING "SentencePiece VERSION.txt not found. Create it or clone full repo.")
    return()
endif()

set(QUIET_SENTENCEPIECE_AVAILABLE ON)

set(SPM_BUILD_TEST OFF CACHE BOOL "Build SentencePiece tests" FORCE)
set(SPM_ENABLE_SHARED OFF CACHE BOOL "Build shared lib" FORCE)
set(SPM_PROTOBUF_PROVIDER "internal" CACHE STRING "Use internal protobuf" FORCE)
set(SPM_ABSL_PROVIDER "internal" CACHE STRING "Use internal absl" FORCE)

add_subdirectory(${third_party_loc}/sentencepiece ${CMAKE_BINARY_DIR}/_deps/sentencepiece_build EXCLUDE_FROM_ALL)

add_library(desktop-app::external_sentencepiece ALIAS sentencepiece)
