# ── ClassicGui Qt 6 Executable ────────────────────────────────────────
#
# All source files for the CLASSIC C++ Qt GUI application.
# AUTOMOC/AUTOUIC/AUTORCC are enabled at the project level.

qt_add_executable(ClassicGui
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
# calling windeployqt on the exe directly gives a flat portable layout:
# DLLs, plugins, and translations all land alongside ClassicGui.exe.
find_program(WINDEPLOYQT_EXECUTABLE windeployqt
    HINTS "${Qt6_DIR}/../../../bin" "${QT_HOST_PATH}/bin"
)
if(WINDEPLOYQT_EXECUTABLE)
    install(CODE "
        execute_process(
            COMMAND \"${WINDEPLOYQT_EXECUTABLE}\"
                \"\${CMAKE_INSTALL_PREFIX}/ClassicGui.exe\"
            WORKING_DIRECTORY \"\${CMAKE_INSTALL_PREFIX}\"
        )
    ")
endif()
