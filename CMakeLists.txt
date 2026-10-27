cmake_minimum_required(VERSION 3.16)

project(ssdeep_parallelisation VERSION 2.14.2 LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(SSDEEP_COMMON_DEFINITIONS
    VERSION="${PROJECT_VERSION}"
    HAVE_STRING_H=1
    HAVE_SYS_STAT_H=1
    HAVE_UNISTD_H=1
    HAVE_INTTYPES_H=1
    HAVE_DIRENT_H=1
    HAVE_SYS_TIME_H=1
    HAVE_SYS_TYPES_H=1
    HAVE_SYS_PARAM_H=1
    HAVE_LIBGEN_H=1
    HAVE_FCNTL_H=1)

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    list(APPEND SSDEEP_COMMON_DEFINITIONS __LINUX__=1)
endif()

set(SSDEEP_CPP_SOURCES
    main.cpp
    match.cpp
    engine.cpp
    filedata.cpp
    dig.cpp
    cycles.cpp
    helpers.cpp
    ui.cpp)

set(SSDEEP_C_SOURCES
    fuzzy.c
    edit_dist.c
    find-file-size.c)

function(add_ssdeep_executable target source_directory)
    set(sources)
    foreach(source IN LISTS SSDEEP_CPP_SOURCES SSDEEP_C_SOURCES)
        list(APPEND sources "${source_directory}/${source}")
    endforeach()

    add_executable(${target} ${sources})
    target_include_directories(${target} PRIVATE "${source_directory}")
    target_compile_definitions(${target} PRIVATE ${SSDEEP_COMMON_DEFINITIONS})
endfunction()

add_ssdeep_executable(ssdeep-original "${CMAKE_CURRENT_SOURCE_DIR}/original")
add_ssdeep_executable(ssdeep-modified "${CMAKE_CURRENT_SOURCE_DIR}/modified")

set(SSDEEP_COMPARISON_BATCH_SIZE 1024 CACHE STRING
    "Number of signature rows calculated before comparison results are handled")
target_compile_definitions(
    ssdeep-modified
    PRIVATE SSDEEP_COMPARISON_BATCH_SIZE=${SSDEEP_COMPARISON_BATCH_SIZE})

find_package(OpenMP REQUIRED COMPONENTS CXX)
target_link_libraries(ssdeep-modified PRIVATE OpenMP::OpenMP_CXX)

set_target_properties(
    ssdeep-original
    ssdeep-modified
    PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

include(CTest)
if(BUILD_TESTING)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_test(
        NAME output-equivalence
        COMMAND
            "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/verify_outputs.py"
            "$<TARGET_FILE:ssdeep-original>"
            "$<TARGET_FILE:ssdeep-modified>")
endif()
