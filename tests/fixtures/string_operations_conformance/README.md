# String operation fixtures

Input-only requests exercise interning, scalar normalization and ordered batch
normalization. Expectations live in `tests/conformance/packs/string_operations`.
Unicode and empty batches are intentional; adapters must preserve input order.
