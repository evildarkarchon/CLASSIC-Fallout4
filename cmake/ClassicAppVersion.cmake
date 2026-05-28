include_guard(GLOBAL)

function(classic_extract_main_yaml_version yaml_path out_var)
    if(NOT EXISTS "${yaml_path}")
        message(FATAL_ERROR
            "Could not find CLASSIC Main.yaml:\n"
            "  ${yaml_path}\n"
            "This file is the documented single source of truth for the "
            "application version.")
    endif()

    file(STRINGS "${yaml_path}" _classic_main_yaml_lines)

    set(_classic_in_info_section FALSE)
    set(_classic_info_child_indent "")

    foreach(_classic_line IN LISTS _classic_main_yaml_lines)
        string(REGEX REPLACE "^[ \t]+" "" _classic_trimmed "${_classic_line}")

        if("${_classic_trimmed}" STREQUAL "" OR _classic_trimmed MATCHES "^#")
            continue()
        endif()

        if(NOT _classic_line MATCHES "^[ \t]")
            string(REGEX REPLACE "[ \t]*#.*$" "" _classic_header "${_classic_trimmed}")
            string(STRIP "${_classic_header}" _classic_header)
            if(_classic_header STREQUAL "CLASSIC_Info:")
                set(_classic_in_info_section TRUE)
                set(_classic_info_child_indent "")
            else()
                set(_classic_in_info_section FALSE)
            endif()
            continue()
        endif()

        if(NOT _classic_in_info_section)
            continue()
        endif()

        string(REGEX MATCH "^[ \t]+" _classic_indent "${_classic_line}")
        if("${_classic_info_child_indent}" STREQUAL "")
            set(_classic_info_child_indent "${_classic_indent}")
        endif()
        if(NOT "${_classic_indent}" STREQUAL "${_classic_info_child_indent}")
            continue()
        endif()

        if(NOT _classic_trimmed MATCHES "^version:")
            continue()
        endif()

        string(REGEX REPLACE "^version:[ \t]*" "" _classic_value "${_classic_trimmed}")
        string(REGEX REPLACE "[ \t]+#.*$" "" _classic_value "${_classic_value}")
        string(STRIP "${_classic_value}" _classic_value)

        if(_classic_value MATCHES "^\"(.*)\"$")
            set(_classic_value "${CMAKE_MATCH_1}")
        elseif(_classic_value MATCHES "^'(.*)'$")
            set(_classic_value "${CMAKE_MATCH_1}")
        endif()

        if(_classic_value MATCHES "^[vV]?([0-9]+\\.[0-9]+\\.[0-9]+)$")
            set(${out_var} "${CMAKE_MATCH_1}" PARENT_SCOPE)
            return()
        endif()

        message(FATAL_ERROR
            "Failed to parse SemVer from CLASSIC_Info.version line:\n"
            "  ${_classic_line}\n"
            "Expected `CLASSIC_Info.version: v<MAJOR>.<MINOR>.<PATCH>`.")
    endforeach()

    message(FATAL_ERROR
        "Could not locate `CLASSIC_Info.version: v<MAJOR>.<MINOR>.<PATCH>` in:\n"
        "  ${yaml_path}\n"
        "This file is the documented single source of truth for the "
        "application version.")
endfunction()
