find_package(Qt6 QUIET COMPONENTS Test)
if(NOT Qt6Test_FOUND)
    message(STATUS "Qt6::Test not found -- classic-gui unit tests disabled")
    return()
endif()

set(CLASSIC_GUI_TEST_TIMEOUT_SECONDS 600 CACHE STRING
    "Timeout (seconds) for classic-gui CTest tests")

set(_classic_gui_qt_bin_dir "")
foreach(_bin_candidate
        "${Qt6_DIR}/../../bin"
        "${Qt6_DIR}/../../../bin"
        "${QT_HOST_PATH}/bin")
    if(EXISTS "${_bin_candidate}")
        set(_classic_gui_qt_bin_dir "${_bin_candidate}")
        break()
    endif()
endforeach()

if(_classic_gui_qt_bin_dir STREQUAL "")
    set(_classic_gui_qt_bin_dir "${Qt6_DIR}/../../../bin")
endif()

set(_classic_gui_qt_plugins_dir "")
foreach(_plugins_candidate
        "${Qt6_DIR}/../../Qt6/plugins"
        "${Qt6_DIR}/../../plugins"
        "${Qt6_DIR}/../../../plugins")
    if(EXISTS "${_plugins_candidate}/platforms")
        set(_classic_gui_qt_plugins_dir "${_plugins_candidate}")
        break()
    endif()
endforeach()

if(_classic_gui_qt_plugins_dir STREQUAL "")
    set(_classic_gui_qt_plugins_dir "${Qt6_DIR}/../../plugins")
endif()

set(_classic_gui_qt_platforms_dir "${_classic_gui_qt_plugins_dir}/platforms")

set(CLASSIC_GUI_TEST_QPA_PLATFORM "offscreen")
set(_classic_gui_qoffscreen_found FALSE)
foreach(_plugin_file
        qoffscreen.dll
        libqoffscreen.so
        libqoffscreen.dylib
        qoffscreen)
    if(EXISTS "${_classic_gui_qt_platforms_dir}/${_plugin_file}")
        set(_classic_gui_qoffscreen_found TRUE)
        break()
    endif()
endforeach()

set(_classic_gui_qminimal_found FALSE)
foreach(_plugin_file
        qminimal.dll
        libqminimal.so
        libqminimal.dylib
        qminimal)
    if(EXISTS "${_classic_gui_qt_platforms_dir}/${_plugin_file}")
        set(_classic_gui_qminimal_found TRUE)
        break()
    endif()
endforeach()

if(NOT _classic_gui_qoffscreen_found)
    if(_classic_gui_qminimal_found)
        set(CLASSIC_GUI_TEST_QPA_PLATFORM "minimal")
    else()
        message(FATAL_ERROR
            "classic-gui tests require a headless Qt platform plugin (offscreen or minimal), "
            "but neither was found in ${_classic_gui_qt_platforms_dir}")
    endif()
endif()

message(STATUS
    "classic-gui tests: QT_PLUGIN_PATH=${_classic_gui_qt_plugins_dir}, QT_QPA_PLATFORM=${CLASSIC_GUI_TEST_QPA_PLATFORM}")

function(add_classic_gui_qt_test target)
    add_executable(${target}
        ${ARGN}
    )

    target_include_directories(${target} PRIVATE
        ${CMAKE_SOURCE_DIR}/src
    )

    target_link_libraries(${target} PRIVATE
        Qt6::Test
        Qt6::Widgets
    )

    if(MSVC)
        target_compile_options(${target} PRIVATE /utf-8 /W4)
    endif()

    add_test(NAME ${target} COMMAND ${target})
    set_tests_properties(${target} PROPERTIES
        ENVIRONMENT "QT_QPA_PLATFORM=${CLASSIC_GUI_TEST_QPA_PLATFORM};QT_PLUGIN_PATH=${_classic_gui_qt_plugins_dir};QT_QPA_PLATFORM_PLUGIN_PATH=${_classic_gui_qt_platforms_dir}"
        ENVIRONMENT_MODIFICATION "PATH=path_list_prepend:${_classic_gui_qt_bin_dir}"
        TIMEOUT ${CLASSIC_GUI_TEST_TIMEOUT_SECONDS}
    )
endfunction()

function(link_classic_gui_rust_bridge target)
    target_link_libraries(${target} PRIVATE
        classic_cxx_bridge
    )

    if(WIN32)
        target_link_libraries(${target} PRIVATE
            ws2_32
            bcrypt
            userenv
            ntdll
            advapi32
            crypt32
            secur32
            ncrypt
            shell32
            ole32
            synchronization
        )
    endif()
endfunction()

add_classic_gui_qt_test(classic-gui-test-reportmetadata
    test_reportmetadatawidget.cpp
    ${CMAKE_SOURCE_DIR}/src/widgets/reportmetadatawidget.cpp
)

add_classic_gui_qt_test(classic-gui-test-reportlist
    test_reportlistwidget.cpp
    ${CMAKE_SOURCE_DIR}/src/core/reportpathkey.cpp
    ${CMAKE_SOURCE_DIR}/src/widgets/reportlistwidget.cpp
)

add_classic_gui_qt_test(classic-gui-test-signalhub
    test_signalhub.cpp
    ${CMAKE_SOURCE_DIR}/src/core/signalhub.cpp
)

add_classic_gui_qt_test(classic-gui-test-threadmanager
    test_threadmanager.cpp
    ${CMAKE_SOURCE_DIR}/src/core/threadmanager.cpp
)

add_classic_gui_qt_test(classic-gui-test-markdownviewer
    test_markdownviewer.cpp
    ${CMAKE_SOURCE_DIR}/src/widgets/markdownviewer.cpp
)
link_classic_gui_rust_bridge(classic-gui-test-markdownviewer)

add_classic_gui_qt_test(classic-gui-test-resultscontroller
    test_resultscontroller.cpp
    ${CMAKE_SOURCE_DIR}/src/controllers/resultscontroller.cpp
    ${CMAKE_SOURCE_DIR}/src/core/reportpathkey.cpp
    ${CMAKE_SOURCE_DIR}/src/core/signalhub.cpp
    ${CMAKE_SOURCE_DIR}/src/widgets/reportlistwidget.cpp
    ${CMAKE_SOURCE_DIR}/src/widgets/markdownviewer.cpp
    ${CMAKE_SOURCE_DIR}/src/widgets/reportmetadatawidget.cpp
)
link_classic_gui_rust_bridge(classic-gui-test-resultscontroller)

add_classic_gui_qt_test(classic-gui-test-mainwindow-geometry
    test_mainwindow_geometry.cpp
)

add_classic_gui_qt_test(classic-gui-test-gamepathutils
    test_gamepathutils.cpp
)

add_classic_gui_qt_test(classic-gui-test-game-setup-user-settings
    test_gamesetupusersettings.cpp
    ${CMAKE_SOURCE_DIR}/src/core/gamesetupusersettings.cpp
)
link_classic_gui_rust_bridge(classic-gui-test-game-setup-user-settings)

add_classic_gui_qt_test(classic-gui-test-gui-user-settings
    test_guiusersettings.cpp
    ${CMAKE_SOURCE_DIR}/src/core/guiusersettings.cpp
)
link_classic_gui_rust_bridge(classic-gui-test-gui-user-settings)

add_classic_gui_qt_test(classic-gui-test-settings-dialog-behavior
    test_settingsdialog_behavior.cpp
    ${CMAKE_SOURCE_DIR}/src/app/settingsdialog.cpp
    ${CMAKE_SOURCE_DIR}/src/core/guiusersettings.cpp
    ${CMAKE_SOURCE_DIR}/src/core/signalhub.cpp
    ${CMAKE_SOURCE_DIR}/src/widgets/toggleswitch.cpp
    ${CMAKE_SOURCE_DIR}/src/workers/yamlupdateworker.cpp
)
target_link_libraries(classic-gui-test-settings-dialog-behavior PRIVATE Qt6::Network)
link_classic_gui_rust_bridge(classic-gui-test-settings-dialog-behavior)

add_classic_gui_qt_test(classic-gui-test-scan-settings-wiring
    test_scan_settings_wiring.cpp
)

add_classic_gui_qt_test(classic-gui-test-scan-progress-model
    test_scan_progress_model.cpp
    ${CMAKE_SOURCE_DIR}/src/workers/scanprogressmodel.cpp
)
link_classic_gui_rust_bridge(classic-gui-test-scan-progress-model)

add_classic_gui_qt_test(classic-gui-test-scan-request-builder
    test_scanrequestbuilder.cpp
    ${CMAKE_SOURCE_DIR}/src/core/guiusersettings.cpp
    ${CMAKE_SOURCE_DIR}/src/workers/scanrequestbuilder.cpp
)
link_classic_gui_rust_bridge(classic-gui-test-scan-request-builder)

add_classic_gui_qt_test(classic-gui-test-scanworker-cancellation
    test_scanworker_cancellation.cpp
    ${CMAKE_SOURCE_DIR}/src/workers/scanworker.cpp
    ${CMAKE_SOURCE_DIR}/src/workers/scanrequestbuilder.cpp
    ${CMAKE_SOURCE_DIR}/src/workers/scanprogressmodel.cpp
)
link_classic_gui_rust_bridge(classic-gui-test-scanworker-cancellation)

# YAML Data bridge round-trip for the GUI counterpart.
# Exercises the first-party `classic::update::yaml_data_*` helpers through
# the same CXX header the GUI controllers use, while the test file also keeps
# a small lower-level compatibility smoke check.
add_classic_gui_qt_test(classic-gui-test-yaml-update-bridge
    test_yaml_update_bridge.cpp
)
link_classic_gui_rust_bridge(classic-gui-test-yaml-update-bridge)

# yaml-update-delivery Section 12 wiring — source-inspection tests that
# verify SettingsDialog and classic-cli consume the bridge correctly (button
# wiring, Update Check setting forwarding, confirm-before-apply ordering).
# Does NOT link the Rust bridge because it reads source files rather than
# exercising FFI at runtime.
add_classic_gui_qt_test(classic-gui-test-yaml-update-wiring
    test_yaml_update_wiring.cpp
)
