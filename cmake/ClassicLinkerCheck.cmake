# Verify that the linker CMake selected for an MSVC configure is really
# Microsoft's linker, not Git for Windows' coreutils `link.exe`. Git
# ships `<git>\usr\bin\link.exe` (a GNU `link` that only creates POSIX
# hardlinks), and shells that prepend Git's `usr/bin` can still confuse
# ad hoc PATH-based checks.
#
# Prefer the concrete linker CMake already resolved (`CMAKE_LINKER`, or
# the compiler-adjacent `link.exe`) because generated Ninja rules use
# that full path directly. Fall back to PATH only when configure has not
# resolved a linker yet.

function(classic_assert_msvc_linker)
    if(NOT WIN32)
        return()
    endif()
    if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
        return()
    endif()

    set(_classic_link_exe "")
    set(_classic_link_resolution "")

    if(CMAKE_LINKER AND EXISTS "${CMAKE_LINKER}")
        set(_classic_link_exe "${CMAKE_LINKER}")
        set(_classic_link_resolution "CMAKE_LINKER")
    elseif(CMAKE_CXX_COMPILER AND EXISTS "${CMAKE_CXX_COMPILER}")
        get_filename_component(_classic_compiler_dir "${CMAKE_CXX_COMPILER}" DIRECTORY)
        set(_classic_compiler_sibling_link "${_classic_compiler_dir}/link.exe")
        if(EXISTS "${_classic_compiler_sibling_link}")
            set(_classic_link_exe "${_classic_compiler_sibling_link}")
            set(_classic_link_resolution "compiler-adjacent link.exe")
        endif()
    endif()

    if(NOT _classic_link_exe)
        # Last-resort fallback for shells where CMake is still relying on
        # PATH-based discovery during the first configure.
        find_program(_classic_link_exe
            NAMES link.exe
            NO_CACHE)
        if(_classic_link_exe)
            set(_classic_link_resolution "PATH")
        endif()
    endif()

    if(NOT _classic_link_exe)
        message(FATAL_ERROR
            "Could not resolve link.exe from CMAKE_LINKER, the compiler "
            "directory, or PATH. Configure must run from a Visual Studio "
            "Developer environment (a VS Dev PowerShell, or after sourcing "
            "tools/use_msvc_from_git_bash.sh from Git Bash).")
    endif()

    # Behavioral probe: MSVC's linker always emits `Microsoft (R)` on its
    # banner. Git's coreutils `link` emits `link: missing operand`. A
    # path heuristic (e.g. looking for `Hostx64\x64`) is fragile across
    # MSVC versions, side-by-side toolsets, and vcvarsall variants -- the
    # behavioral check is identity-based and survives all of those.
    execute_process(
        COMMAND "${_classic_link_exe}"
        OUTPUT_VARIABLE _classic_link_stdout
        ERROR_VARIABLE _classic_link_stderr
        RESULT_VARIABLE _classic_link_exit
        TIMEOUT 5)

    set(_classic_link_combined "${_classic_link_stdout}${_classic_link_stderr}")
    if(_classic_link_combined MATCHES "Microsoft \\(R\\)")
        message(STATUS
            "MSVC linker verified via ${_classic_link_resolution}: "
            "${_classic_link_exe}")
        return()
    endif()

    get_filename_component(_classic_link_dir "${_classic_link_exe}" DIRECTORY)
    if(_classic_link_resolution STREQUAL "PATH")
        set(_classic_resolution_details
            "PATH resolved to a non-MSVC linker. This is almost certainly "
            "Git for Windows' coreutils `link.exe` shadowing the Visual "
            "Studio toolset during configure.")
        set(_classic_remediation_lines
            "  - Run from a Visual Studio Developer PowerShell (cl.exe, "
            "link.exe, lib.exe all on PATH from MSVC).\n"
            "  - From Git Bash, source `tools/use_msvc_from_git_bash.sh` "
            "first.\n"
            "  - Or remove `<git>\\usr\\bin` from PATH for this shell, or "
            "move it after `<VS>\\VC\\Tools\\MSVC\\<ver>\\bin\\Hostx64\\x64`.")
    else()
        set(_classic_resolution_details
            "CMake resolved a concrete linker path, but that executable "
            "does not identify itself as the Microsoft linker.")
        set(_classic_remediation_lines
            "  - Inspect the active CMake preset, kit, and toolchain file.\n"
            "  - Make sure CMAKE_LINKER (or the selected compiler path) "
            "points at the Visual Studio toolset.\n"
            "  - From Git Bash, source `tools/use_msvc_from_git_bash.sh` "
            "first if you expect PATH-based discovery.")
    endif()

    message(FATAL_ERROR
        "Resolved linker is NOT the MSVC linker:\n"
        "  ${_classic_link_exe}\n"
        "  (parent: ${_classic_link_dir})\n"
        "Resolution source: ${_classic_link_resolution}\n"
        "Probe output (no-args invocation):\n"
        "  stdout: ${_classic_link_stdout}\n"
        "  stderr: ${_classic_link_stderr}\n"
        "${_classic_resolution_details}\n"
        "Remediation:\n"
        "${_classic_remediation_lines}")
endfunction()
