if(NOT DEFINED CLASSIC_APP_VERSION_MODULE)
    set(CLASSIC_APP_VERSION_MODULE "${CMAKE_CURRENT_LIST_DIR}/ClassicAppVersion.cmake")
elseif(NOT IS_ABSOLUTE "${CLASSIC_APP_VERSION_MODULE}")
    set(CLASSIC_APP_VERSION_MODULE
        "${CMAKE_CURRENT_LIST_DIR}/../${CLASSIC_APP_VERSION_MODULE}")
endif()
get_filename_component(CLASSIC_APP_VERSION_MODULE
    "${CLASSIC_APP_VERSION_MODULE}" ABSOLUTE)
file(TO_CMAKE_PATH "${CLASSIC_APP_VERSION_MODULE}" CLASSIC_APP_VERSION_MODULE)

if(NOT DEFINED CLASSIC_APP_VERSION_MODULE OR
        NOT EXISTS "${CLASSIC_APP_VERSION_MODULE}")
    message(FATAL_ERROR
        "CLASSIC_APP_VERSION_MODULE must point to "
        "cmake/ClassicAppVersion.cmake.")
endif()

include("${CLASSIC_APP_VERSION_MODULE}")

string(RANDOM LENGTH 12 ALPHABET 0123456789abcdef _classic_test_id)
file(TO_CMAKE_PATH "$ENV{TEMP}" _classic_temp_root)
if(NOT _classic_temp_root)
    set(_classic_temp_root "${CMAKE_CURRENT_LIST_DIR}")
endif()
set(_classic_temp_dir
    "${_classic_temp_root}/classic-app-version-test-${_classic_test_id}")
file(MAKE_DIRECTORY "${_classic_temp_dir}")

function(_classic_expect_version label yaml_text expected_version)
    set(_yaml_path "${_classic_temp_dir}/${label}/CLASSIC Main.yaml")
    get_filename_component(_yaml_dir "${_yaml_path}" DIRECTORY)
    file(MAKE_DIRECTORY "${_yaml_dir}")
    file(WRITE "${_yaml_path}" "${yaml_text}")

    classic_extract_main_yaml_version("${_yaml_path}" _actual_version)

    if(NOT _actual_version STREQUAL expected_version)
        message(FATAL_ERROR
            "${label}: expected ${expected_version}, got ${_actual_version}")
    endif()
endfunction()

function(_classic_expect_failure label yaml_text expected_error_fragment)
    set(_yaml_path "${_classic_temp_dir}/${label}/CLASSIC Main.yaml")
    set(_script_path "${_classic_temp_dir}/${label}/extract.cmake")
    get_filename_component(_yaml_dir "${_yaml_path}" DIRECTORY)
    file(MAKE_DIRECTORY "${_yaml_dir}")
    file(WRITE "${_yaml_path}" "${yaml_text}")
    file(TO_CMAKE_PATH "${_yaml_path}" _child_yaml_path)
    file(WRITE "${_script_path}"
        "include(\"${CLASSIC_APP_VERSION_MODULE}\")\n"
        "classic_extract_main_yaml_version(\"${_child_yaml_path}\" _version)\n")

    execute_process(
        COMMAND "${CMAKE_COMMAND}" -P "${_script_path}"
        RESULT_VARIABLE _result
        OUTPUT_VARIABLE _stdout
        ERROR_VARIABLE _stderr
    )

    if(_result EQUAL 0)
        message(FATAL_ERROR
            "${label}: expected extractor failure, but it succeeded.")
    endif()

    string(CONCAT _combined_output "${_stdout}" "${_stderr}")
    if(NOT _combined_output MATCHES "${expected_error_fragment}")
        message(FATAL_ERROR
            "${label}: expected failure output to contain "
            "'${expected_error_fragment}', got:\n${_combined_output}")
    endif()
endfunction()

_classic_expect_version("game-version-before-classic-info" [=[
schema_version: "2.0"

Game_Data:
  versions:
    - id: FO4_OG
      game: Fallout4
      version: 1.10.163.0

CLASSIC_Info:
  version: v9.1.0
  version_date: 26.04.19
  is_prerelease: false
]=] "9.1.0")

_classic_expect_version("quoted-classic-info-version-with-comment" [=[
schema_version: "2.0"

CLASSIC_Info:
  version: "V9.2.3" # release version

Game_Data:
  versions:
    - id: FO4_NG
      version: "1.10.984.0"
]=] "9.2.3")

_classic_expect_failure("rejects-extra-version-components" [=[
schema_version: "2.0"

CLASSIC_Info:
  version: v9.1.0.7
]=] "Expected `CLASSIC_Info.version: v<MAJOR>.<MINOR>.<PATCH>`")

file(REMOVE_RECURSE "${_classic_temp_dir}")
