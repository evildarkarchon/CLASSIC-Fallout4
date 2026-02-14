find_package(Qt6 QUIET COMPONENTS Test)
if(NOT Qt6Test_FOUND)
    message(STATUS "Qt6::Test not found -- classic-gui unit tests disabled")
    return()
endif()

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
    set(_qt_bin_dir "${Qt6_DIR}/../../../bin")
    set_tests_properties(${target} PROPERTIES
        ENVIRONMENT "QT_QPA_PLATFORM=offscreen"
        ENVIRONMENT_MODIFICATION "PATH=path_list_prepend:${_qt_bin_dir}"
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
