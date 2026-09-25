# Extended Version Registry scenarios

Input-only requests use identical authored `registryYaml` bytes and a temporary working directory. They exercise additional Node/Python registry queries unavailable through CXX: lookups, mode filters, address resolution, hash collections, crash-generator version strings, policy defaults and compatibility. Expected values are authored separately in `tests/conformance/packs/version_registry_details/v1.json`.

The malformed version scenario must return a native parse error. Every scenario forbids changes to the seed YAML and additional filesystem entries. Dedicated participant processes prevent an unrelated singleton initialization from selecting contributor settings.
