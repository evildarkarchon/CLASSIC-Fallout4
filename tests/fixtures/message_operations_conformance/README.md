# Message Operations fixtures

Each request supplies a message type, routing target, content and nullable details.
The Rust participant creates a real public message and calls the public
formatter. The output retains type, target, content, nullable title and
details, and exact formatted text. Rust uses the public details builder.

Cases preserve the distinction between absent and empty details, empty content,
multiline text and Unicode. All seven message types and the four routing targets
appear. CXX exposes logging operations but no message creation or
formatting API, so it is not a participant. No fixture captures global log output.
Expectations live in `tests/conformance/packs/message_operations/v1.json`.
