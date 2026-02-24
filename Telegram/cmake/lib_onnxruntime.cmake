# ONNX Runtime from source (for Quiet ML only).
# Requires: Telegram/ThirdParty/onnxruntime cloned (see README or run git clone).
# Build also requires Python (for ONNX Runtime's gen_def.py).
set(QUIET_ONNX_AVAILABLE OFF)

if (NOT EXISTS "${third_party_loc}/onnxruntime/cmake/CMakeLists.txt")
    message(WARNING "ONNX Runtime source not found at ${third_party_loc}/onnxruntime. Quiet ONNX support disabled. Clone with: git clone --depth 1 https://github.com/microsoft/onnxruntime.git Telegram/ThirdParty/onnxruntime")
    set(QUIET_ONNX_AVAILABLE OFF)
    return()
endif()

if (CMAKE_VERSION VERSION_LESS "3.28")
    message(WARNING "ONNX Runtime requires CMake 3.28+. Current: ${CMAKE_VERSION}. Quiet ONNX support disabled.")
    set(QUIET_ONNX_AVAILABLE OFF)
    return()
endif()

set(QUIET_ONNX_AVAILABLE ON)
set(onnxruntime_build_dir ${CMAKE_BINARY_DIR}/_deps/onnxruntime_build)
set(onnxruntime_source_cmake "${third_party_loc}/onnxruntime/cmake")

include(ExternalProject)
set(onnxruntime_byproducts "")
if (WIN32)
    list(APPEND onnxruntime_byproducts
        ${onnxruntime_build_dir}/bin/Release/onnxruntime.dll
        ${onnxruntime_build_dir}/bin/Release/onnxruntime.lib
    )
elseif (APPLE)
    list(APPEND onnxruntime_byproducts ${onnxruntime_build_dir}/libonnxruntime.dylib)
else()
    list(APPEND onnxruntime_byproducts ${onnxruntime_build_dir}/libonnxruntime.so)
endif()

ExternalProject_Add(onnxruntime_ext
    SOURCE_DIR ${third_party_loc}/onnxruntime
    BINARY_DIR ${onnxruntime_build_dir}
    CONFIGURE_COMMAND ${CMAKE_COMMAND}
        -S ${onnxruntime_source_cmake}
        -B ${onnxruntime_build_dir}
        -Donnxruntime_BUILD_SHARED_LIB=ON
        -Donnxruntime_BUILD_UNIT_TESTS=OFF
        -Donnxruntime_BUILD_BENCHMARKS=OFF
        -Donnxruntime_BUILD_CSHARP=OFF
        -Donnxruntime_BUILD_OBJC=OFF
        -Donnxruntime_ENABLE_PYTHON=OFF
        -Donnxruntime_USE_CUDA=OFF
        -Donnxruntime_USE_VCPKG=OFF
        -DCMAKE_INSTALL_PREFIX=${CMAKE_BINARY_DIR}/_deps/onnxruntime_install
        -DCMAKE_POSITION_INDEPENDENT_CODE=ON
    BUILD_COMMAND ${CMAKE_COMMAND} --build ${onnxruntime_build_dir} --config $<CONFIG>
    INSTALL_COMMAND ""
    BUILD_BYPRODUCTS ${onnxruntime_byproducts}
    EXCLUDE_FROM_ALL ON
)

# Include dir for headers: use only source tree (build/include does not exist until after build)
set(onnxruntime_include_dirs ${third_party_loc}/onnxruntime/include)

add_library(desktop-app::external_onnxruntime INTERFACE IMPORTED GLOBAL)
add_dependencies(desktop-app::external_onnxruntime onnxruntime_ext)
target_include_directories(desktop-app::external_onnxruntime INTERFACE ${onnxruntime_include_dirs})

if (WIN32)
    set(onnxruntime_lib_release "${onnxruntime_build_dir}/bin/Release/onnxruntime.dll")
    set(onnxruntime_lib_release_lib "${onnxruntime_build_dir}/bin/Release/onnxruntime.lib")
    set(onnxruntime_lib_debug "${onnxruntime_build_dir}/bin/Debug/onnxruntime.dll")
    set(onnxruntime_lib_debug_lib "${onnxruntime_build_dir}/bin/Debug/onnxruntime.lib")
    target_link_libraries(desktop-app::external_onnxruntime INTERFACE
        $<$<CONFIG:Release>:${onnxruntime_lib_release_lib}>
        $<$<CONFIG:RelWithDebInfo>:${onnxruntime_build_dir}/bin/RelWithDebInfo/onnxruntime.lib>
        $<$<CONFIG:Debug>:${onnxruntime_lib_debug_lib}>
        $<$<CONFIG:MinSizeRel>:${onnxruntime_build_dir}/bin/MinSizeRel/onnxruntime.lib>
    )
    target_link_directories(desktop-app::external_onnxruntime INTERFACE
        $<$<CONFIG:Release>:${onnxruntime_build_dir}/bin/Release>
        $<$<CONFIG:RelWithDebInfo>:${onnxruntime_build_dir}/bin/RelWithDebInfo>
        $<$<CONFIG:Debug>:${onnxruntime_build_dir}/bin/Debug>
        $<$<CONFIG:MinSizeRel>:${onnxruntime_build_dir}/bin/MinSizeRel>
    )
elseif (APPLE)
    target_link_libraries(desktop-app::external_onnxruntime INTERFACE
        ${onnxruntime_build_dir}/libonnxruntime.dylib
    )
    target_link_directories(desktop-app::external_onnxruntime INTERFACE ${onnxruntime_build_dir})
else()
    target_link_libraries(desktop-app::external_onnxruntime INTERFACE
        ${onnxruntime_build_dir}/libonnxruntime.so
    )
    target_link_directories(desktop-app::external_onnxruntime INTERFACE ${onnxruntime_build_dir})
endif()

# Quiet-only wrapper library: links ONNX Runtime so only Quiet code depends on it.
# When included from Telegram/CMakeLists.txt, CMAKE_CURRENT_SOURCE_DIR is Telegram/.
set(telegram_src_loc "${CMAKE_CURRENT_SOURCE_DIR}/SourceFiles")
add_library(lib_quiet_onnx STATIC)
init_target(lib_quiet_onnx)
add_library(tdesktop::lib_quiet_onnx ALIAS lib_quiet_onnx)

target_sources(lib_quiet_onnx PRIVATE
    ${telegram_src_loc}/quiet/quiet_onnx_stub.cpp
    ${telegram_src_loc}/quiet/ml/summarizer.cpp
)
if (QUIET_SENTENCEPIECE_AVAILABLE)
    target_sources(lib_quiet_onnx PRIVATE ${telegram_src_loc}/quiet/ml/tokenizer.cpp)
    target_include_directories(lib_quiet_onnx PRIVATE ${third_party_loc}/sentencepiece/src)
endif()
target_include_directories(lib_quiet_onnx PRIVATE ${telegram_src_loc})
target_link_libraries(lib_quiet_onnx PUBLIC desktop-app::external_onnxruntime desktop-app::external_qt)
if (TARGET desktop-app::external_sentencepiece)
    target_link_libraries(lib_quiet_onnx PUBLIC desktop-app::external_sentencepiece)
endif()
