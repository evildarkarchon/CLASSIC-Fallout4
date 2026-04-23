# Verify that the `link.exe` cl.exe will spawn at link-time is MSVC's
# linker, not Git for Windows' coreutils `link.exe`. Git ships
# `<git>\usr\bin\link.exe` (a GNU `link` that only creates POSIX
# hardlinks). When Git's `usr/bin` precedes MSVC on PATH, Ninja link
# steps fail with cryptic messages like `link: extra operand '/OUT:...'`
# because cl.exe spawns a bare `link` via PATH lookup at link time --
# not via CMake's CMAKE_LINKER variable -- so a "correct" CMAKE_LINKER
# does not save us.
#
# Run this at configure time so the failure surfaces with a remediation
# pointer instead of a misleading mid-build Ninja error.

function(classic_assert_msvc_linker)
    if(NOT WIN32)
        return()
    endif()
    if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
        return()
    endif()

    # Resolve `link.exe` exactly the way cl.exe will at build time: via
    # PATH lookup. NO_CACHE forces a fresh search each configure so a
    # PATH change between shells is never masked by a stale cache entry.
    find_program(_classic_link_exe
        NAMES link.exe
        NO_CACHE)

    if(NOT _classic_link_exe)
        message(FATAL_ERROR
            "Could not find link.exe on PATH. Configure must run from a "
            "Visual Studio Developer environment (a VS Dev PowerShell, or "
            "after sourcing tools/use_msvc_from_git_bash.sh from Git Bash).")
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
        message(STATUS "MSVC linker verified: ${_classic_link_exe}")
        return()
    endif()

    get_filename_component(_classic_link_dir "${_classic_link_exe}" DIRECTORY)
    message(FATAL_ERROR
        "Resolved link.exe is NOT the MSVC linker:\n"
        "  ${_classic_link_exe}\n"
        "  (parent: ${_classic_link_dir})\n"
        "Probe output (no-args invocation):\n"
        "  stdout: ${_classic_link_stdout}\n"
        "  stderr: ${_classic_link_stderr}\n"
        "This is almost certainly Git for Windows' coreutils `link.exe` "
        "shadowing MSVC's link.exe on PATH. cl.exe spawns `link` via PATH "
        "at link time, so Ninja will fail mid-build with cryptic errors "
        "like `link: extra operand '/OUT:...'`.\n"
        "Remediation:\n"
        "  - Run from a Visual Studio Developer PowerShell (cl.exe, "
        "link.exe, lib.exe all on PATH from MSVC).\n"
        "  - From Git Bash, source `tools/use_msvc_from_git_bash.sh` "
        "first.\n"
        "  - Or remove `<git>\\usr\\bin` from PATH for this shell, or "
        "move it after `<VS>\\VC\\Tools\\MSVC\\<ver>\\bin\\Hostx64\\x64`.")
endfunction()
