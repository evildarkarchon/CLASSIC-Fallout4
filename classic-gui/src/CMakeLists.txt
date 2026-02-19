# ── ClassicGui Qt 6 Executable ────────────────────────────────────────
#
# All source files for the CLASSIC C++ Qt GUI application.
# AUTOMOC/AUTOUIC/AUTORCC are enabled at the project level.

qt_add_executable(ClassicGui WIN32
    # Entry point
    main.cpp

    # Application windows and dialogs
    app/mainwindow.h
    app/mainwindow.cpp
    app/errordialog.h
    app/errordialog.cpp
    app/settingsdialog.h
    app/settingsdialog.cpp
    app/aboutdialog.h
    app/aboutdialog.cpp
    app/papyrusdialog.h
    app/papyrusdialog.cpp
    app/pathdialog.h
    app/pathdialog.cpp

    # Core infrastructure
    core/rust_qt_bridge.h
    core/signalhub.h
    core/signalhub.cpp
    core/featurecontext.h
    core/featurecontext.cpp
    core/threadmanager.h
    core/threadmanager.cpp

    # Workers (QThread worker objects)
    workers/scanworker.h
    workers/scanworker.cpp
    workers/gamefilesworker.h
    workers/gamefilesworker.cpp
    workers/papyrusworker.h
    workers/papyrusworker.cpp
    workers/updateworker.h
    workers/updateworker.cpp

    # Widgets (reusable UI components)
    widgets/reportlistwidget.h
    widgets/reportlistwidget.cpp
    widgets/markdownviewer.h
    widgets/markdownviewer.cpp
    widgets/reportmetadatawidget.h
    widgets/reportmetadatawidget.cpp
    widgets/adaptiveprogressbar.h
    widgets/adaptiveprogressbar.cpp
    widgets/toggleswitch.h
    widgets/toggleswitch.cpp

    # Controllers (feature orchestration)
    controllers/scancontroller.h
    controllers/scancontroller.cpp
    controllers/gamefilescontroller.h
    controllers/gamefilescontroller.cpp
    controllers/backupcontroller.h
    controllers/backupcontroller.cpp
    controllers/resultscontroller.h
    controllers/resultscontroller.cpp

    # Qt resources
    ../resources/resources.qrc
)

set_target_properties(ClassicGui PROPERTIES
    OUTPUT_NAME "CLASSIC"
)

# Embed the application icon into the Windows executable so Explorer shows
# CLASSIC.ico instead of the generic binary icon.
if(WIN32)
    set(CLASSIC_GUI_EXE_ICON "${CMAKE_SOURCE_DIR}/../CLASSIC Data/graphics/CLASSIC.ico")
    if(EXISTS "${CLASSIC_GUI_EXE_ICON}")
        string(REPLACE "/" "\\\\" CLASSIC_GUI_EXE_ICON_RC "${CLASSIC_GUI_EXE_ICON}")
        configure_file(
            "${CMAKE_CURRENT_SOURCE_DIR}/classic_gui_icon.rc.in"
            "${CMAKE_CURRENT_BINARY_DIR}/classic_gui_icon.rc"
            @ONLY
        )
        target_sources(ClassicGui PRIVATE
            "${CMAKE_CURRENT_BINARY_DIR}/classic_gui_icon.rc"
        )
    else()
        message(WARNING "CLASSIC GUI executable icon not found: ${CLASSIC_GUI_EXE_ICON}")
    endif()
endif()

# ── Include directories ──────────────────────────────────────────────
# Allow includes like "core/signalhub.h", "app/mainwindow.h"
target_include_directories(ClassicGui PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# ── Link libraries ───────────────────────────────────────────────────
target_link_libraries(ClassicGui PRIVATE
    Qt6::Widgets
    Qt6::Network
    classic_cxx_bridge
)

# ── Windows system libraries required by Rust staticlib ──────────────
if(WIN32)
    target_link_libraries(ClassicGui PRIVATE
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

# ── MSVC-specific flags ─────────────────────────────────────────────
if(MSVC)
    target_compile_options(ClassicGui PRIVATE /utf-8 /W4)
endif()

# ── Install & Deploy ──────────────────────────────────────────────────
# Executable → root of install prefix (portable app layout)
install(TARGETS ClassicGui RUNTIME DESTINATION .)

# Stylesheet → styles/ alongside the exe (loadStylesheet() resolves
# relative to QCoreApplication::applicationDirPath())
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/styles/dark_theme.qss
        DESTINATION styles)

# qt.conf (next to CLASSIC.exe) tells Qt to resolve runtime assets from
# the dedicated Qt6 folder while keeping Qt*.dll in the app directory.
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/qt.conf
        DESTINATION .)

# CLASSIC Data — runtime data files (databases, graphics, help, game versions).
# Only the subdirectories the app actually uses are installed; dev-only files
# (Python/Pascal scripts, zip archive, local config) at the top level are skipped.
set(CLASSIC_DATA_DIR "${CMAKE_SOURCE_DIR}/../CLASSIC Data")

install(DIRECTORY "${CLASSIC_DATA_DIR}/databases/"
    DESTINATION "CLASSIC Data/databases"
    PATTERN "*.db-shm" EXCLUDE
    PATTERN "*.db-wal" EXCLUDE
    PATTERN "*.backup.*" EXCLUDE
    PATTERN "*.sha256" EXCLUDE
)
install(DIRECTORY "${CLASSIC_DATA_DIR}/graphics/"
    DESTINATION "CLASSIC Data/graphics"
)
install(DIRECTORY "${CLASSIC_DATA_DIR}/Help/"
    DESTINATION "CLASSIC Data/Help"
)
install(DIRECTORY "${CLASSIC_DATA_DIR}/games/"
    DESTINATION "CLASSIC Data/games"
)

# Qt deploy — run windeployqt directly on the installed exe.
# Unlike qt_generate_deploy_app_script() which forces a bin/ subdirectory,
# calling windeployqt on the installed exe keeps a portable layout while
# placing plugin/translations assets under Qt6/ via explicit output dirs.
find_program(WINDEPLOYQT_EXECUTABLE windeployqt
    HINTS "${Qt6_DIR}/../../../bin" "${QT_HOST_PATH}/bin"
)
if(WINDEPLOYQT_EXECUTABLE)
    install(CODE "
        execute_process(
            COMMAND \"${WINDEPLOYQT_EXECUTABLE}\"
                --plugindir \"\${CMAKE_INSTALL_PREFIX}/Qt6/plugins\"
                --translationdir \"\${CMAKE_INSTALL_PREFIX}/Qt6/translations\"
                \"\${CMAKE_INSTALL_PREFIX}/CLASSIC.exe\"
            WORKING_DIRECTORY \"\${CMAKE_INSTALL_PREFIX}\"
        )

        # Remove legacy root-level plugin/translations folders left by older
        # flat deployments so install/ stays clean.
        foreach(_legacy_dir generic iconengines imageformats networkinformation platforms tls translations)
            if(EXISTS \"\${CMAKE_INSTALL_PREFIX}/\${_legacy_dir}\")
                file(REMOVE_RECURSE \"\${CMAKE_INSTALL_PREFIX}/\${_legacy_dir}\")
            endif()
        endforeach()

        # styles/ is app-owned for dark_theme.qss; remove stale plugin DLLs
        # that older flat deployments may have placed there.
        if(EXISTS \"\${CMAKE_INSTALL_PREFIX}/styles\")
            file(GLOB _legacy_style_plugins \"\${CMAKE_INSTALL_PREFIX}/styles/*.dll\")
            if(_legacy_style_plugins)
                file(REMOVE \${_legacy_style_plugins})
            endif()
        endif()
    ")
endif()
