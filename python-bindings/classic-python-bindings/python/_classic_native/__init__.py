"""Private home of the one CLASSIC native extension (``_classic_native._native``).

Import the public ``classic_*`` modules instead. Each of the 18 direct-import
facades re-exports the canonical native objects registered on its own native
submodule, ``_classic_native._native.<facade>``. Nothing here is a public
contract: the package name, native filename, and loader may change.
"""
