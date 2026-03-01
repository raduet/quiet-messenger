if(NOT ONNX_SOURCE_DIR)
    message(FATAL_ERROR "ONNX_SOURCE_DIR required")
endif()
set(CMAKELISTS "${ONNX_SOURCE_DIR}/cmake/CMakeLists.txt")
if(NOT EXISTS "${CMAKELISTS}")
    message(FATAL_ERROR "ONNX cmake/CMakeLists.txt not found: ${CMAKELISTS}")
endif()
file(READ "${CMAKELISTS}" CONTENT)
if(CONTENT MATCHES "add_compile_options\\(/FS\\)")
    message(STATUS "ONNX CMakeLists.txt already has /FS patch")
else()
    string(REPLACE
        "project(onnxruntime C CXX ASM)\n\n# Disable fast-math"
        "project(onnxruntime C CXX ASM)\n\n# Force /FS for MSVC (C1041 when multiple cl.exe write to same PDB)\nif(MSVC)\n  add_compile_options(/FS)\nendif()\n\n# Disable fast-math"
        CONTENT "${CONTENT}")
    file(WRITE "${CMAKELISTS}" "${CONTENT}")
    message(STATUS "Patched ONNX cmake/CMakeLists.txt: added add_compile_options(/FS) for MSVC")
endif()
