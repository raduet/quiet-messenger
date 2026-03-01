# ONNX Runtime for Quiet ML: build from Git tag (stable) or use local clone.
# Build requires Python (for ONNX Runtime's gen_def.py).
set(QUIET_ONNX_AVAILABLE OFF)

option(QUIET_USE_ONNX_RUNTIME "Build with ONNX Runtime for Quiet ML (downloads and builds onnxruntime)" ON)
if (NOT QUIET_USE_ONNX_RUNTIME)
    return()
endif()

set(onnxruntime_build_dir ${CMAKE_BINARY_DIR}/_deps/onnxruntime_build)
set(onnxruntime_prefix_dir ${CMAKE_BINARY_DIR}/_deps/onnxruntime_src)
if (EXISTS "${third_party_loc}/onnxruntime/cmake/CMakeLists.txt")
    set(onnxruntime_use_local ON)
    set(onnxruntime_source_dir "${third_party_loc}/onnxruntime")
else()
    set(onnxruntime_use_local OFF)
    set(onnxruntime_source_dir "${onnxruntime_prefix_dir}/src/onnxruntime_ext")
endif()

if (CMAKE_VERSION VERSION_LESS "3.28")
    message(WARNING "ONNX Runtime requires CMake 3.28+. Current: ${CMAKE_VERSION}. Quiet ONNX support disabled.")
    set(QUIET_ONNX_AVAILABLE OFF)
    return()
endif()

set(QUIET_ONNX_AVAILABLE ON)
set(onnxruntime_source_cmake "${onnxruntime_source_dir}/cmake")

include(ProcessorCount)
ProcessorCount(ONNX_BUILD_JOBS)
if(ONNX_BUILD_JOBS EQUAL 0)
    set(ONNX_BUILD_JOBS 1)
endif()

include(ExternalProject)
set(onnxruntime_byproducts "")
if (WIN32)
    foreach(_cfg Debug Release RelWithDebInfo MinSizeRel)
        list(APPEND onnxruntime_byproducts
            ${onnxruntime_build_dir}/${_cfg}/onnxruntime.dll
            ${onnxruntime_build_dir}/${_cfg}/onnxruntime.lib
        )
    endforeach()
elseif (APPLE)
    list(APPEND onnxruntime_byproducts ${onnxruntime_build_dir}/libonnxruntime.dylib)
else()
    list(APPEND onnxruntime_byproducts ${onnxruntime_build_dir}/libonnxruntime.so)
endif()

set(onnxruntime_extra_args "")

set(onnxruntime_ep_source "")
set(onnxruntime_patch_cmd "")
if (onnxruntime_use_local)
    set(onnxruntime_ep_source SOURCE_DIR ${onnxruntime_source_dir})
else()
    set(onnxruntime_ep_source
        GIT_REPOSITORY https://github.com/microsoft/onnxruntime.git
        GIT_TAG v1.18.1
        GIT_SHALLOW TRUE
    )
    set(onnxruntime_patch_cmd PATCH_COMMAND
        ${CMAKE_COMMAND} -DONNX_SOURCE_DIR=<SOURCE_DIR> -P ${CMAKE_CURRENT_LIST_DIR}/patch_onnx_eigen.cmake
        COMMAND ${CMAKE_COMMAND} -DONNX_SOURCE_DIR=<SOURCE_DIR> -P ${CMAKE_CURRENT_LIST_DIR}/patch_onnx_remove_za.cmake
        COMMAND ${CMAKE_COMMAND} -DONNX_SOURCE_DIR=<SOURCE_DIR> -P ${CMAKE_CURRENT_LIST_DIR}/patch_onnx_chrono.cmake
        COMMAND ${CMAKE_COMMAND} -DONNX_SOURCE_DIR=<SOURCE_DIR> -P ${CMAKE_CURRENT_LIST_DIR}/patch_onnx_fs.cmake
        COMMAND ${CMAKE_COMMAND} -DONNX_SOURCE_DIR=<SOURCE_DIR> -P ${CMAKE_CURRENT_LIST_DIR}/patch_onnx_protobuf_rt.cmake
    )
endif()

if (WIN32)
    set(onnxruntime_init_cache "${CMAKE_BINARY_DIR}/onnxruntime_win_cache.cmake")
    file(WRITE "${onnxruntime_init_cache}"
        "set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreadedDebugDLL CACHE STRING \"\" FORCE)\n"
        "set(CMAKE_POLICY_DEFAULT_CMP0091 NEW)\n"
        "set(CMAKE_C_FLAGS \"${CMAKE_C_FLAGS} /FS\" CACHE STRING \"\" FORCE)\n"
        "set(CMAKE_CXX_FLAGS \"${CMAKE_CXX_FLAGS} /FS\" CACHE STRING \"\" FORCE)\n"
        "set(CMAKE_C_FLAGS_DEBUG \"${CMAKE_C_FLAGS_DEBUG} /FS\" CACHE STRING \"\" FORCE)\n"
        "set(CMAKE_CXX_FLAGS_DEBUG \"${CMAKE_CXX_FLAGS_DEBUG} /FS\" CACHE STRING \"\" FORCE)\n"
    )
endif()

ExternalProject_Add(onnxruntime_ext
    PREFIX ${onnxruntime_prefix_dir}
    ${onnxruntime_ep_source}
    BINARY_DIR ${onnxruntime_build_dir}
    CONFIGURE_COMMAND ${CMAKE_COMMAND}
        $<$<BOOL:${WIN32}>:-C ${onnxruntime_init_cache}>
        -S <SOURCE_DIR>/cmake
        -B ${onnxruntime_build_dir}
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5
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
        -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebugDLL
        ${onnxruntime_extra_args}
    ${onnxruntime_patch_cmd}
    BUILD_COMMAND ${CMAKE_COMMAND} --build ${onnxruntime_build_dir} --config $<CONFIG> --parallel ${ONNX_BUILD_JOBS} $<$<BOOL:${WIN32}>:-- /m:${ONNX_BUILD_JOBS}>
    INSTALL_COMMAND ""
    BUILD_BYPRODUCTS ${onnxruntime_byproducts}
    EXCLUDE_FROM_ALL ON
    LOG_DOWNLOAD ON
    LOG_CONFIGURE ON
    LOG_BUILD ON
)

ExternalProject_Get_Property(onnxruntime_ext SOURCE_DIR)
file(MAKE_DIRECTORY "${SOURCE_DIR}/include")
add_library(desktop-app::external_onnxruntime INTERFACE IMPORTED GLOBAL)
add_dependencies(desktop-app::external_onnxruntime onnxruntime_ext)
target_include_directories(desktop-app::external_onnxruntime INTERFACE ${SOURCE_DIR}/include)

if (WIN32)
    set(onnxruntime_lib_release "${onnxruntime_build_dir}/Release/onnxruntime.dll")
    set(onnxruntime_lib_release_lib "${onnxruntime_build_dir}/Release/onnxruntime.lib")
    set(onnxruntime_lib_debug "${onnxruntime_build_dir}/Debug/onnxruntime.dll")
    set(onnxruntime_lib_debug_lib "${onnxruntime_build_dir}/Debug/onnxruntime.lib")
    target_link_libraries(desktop-app::external_onnxruntime INTERFACE
        $<$<CONFIG:Release>:${onnxruntime_lib_release_lib}>
        $<$<CONFIG:RelWithDebInfo>:${onnxruntime_build_dir}/RelWithDebInfo/onnxruntime.lib>
        $<$<CONFIG:Debug>:${onnxruntime_lib_debug_lib}>
        $<$<CONFIG:MinSizeRel>:${onnxruntime_build_dir}/MinSizeRel/onnxruntime.lib>
    )
    target_link_directories(desktop-app::external_onnxruntime INTERFACE
        $<$<CONFIG:Release>:${onnxruntime_build_dir}/Release>
        $<$<CONFIG:RelWithDebInfo>:${onnxruntime_build_dir}/RelWithDebInfo>
        $<$<CONFIG:Debug>:${onnxruntime_build_dir}/Debug>
        $<$<CONFIG:MinSizeRel>:${onnxruntime_build_dir}/MinSizeRel>
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
