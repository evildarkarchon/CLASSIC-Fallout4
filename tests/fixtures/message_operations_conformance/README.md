# Message Operations fixtures

Each request supplies a message type, routing target, content and nullable details.
The Rust, Node and Python participants create a real public message and call the
public formatter. The output retains type, target, content, nullable title and
details, and exact formatted text. Node exposes details as a documented mutable
plain-object formatter input; Rust and Python use the public details builder.

Cases preserve the distinction between absent and empty details, empty content,
multiline text and Unicode. All seven message types and the four routing targets
shared by these bindings appear. Node's wall-clock timestamp is outside this stable
domain projection. CXX exposes logging operations but no message creation or
formatting API, so it is not a participant. No fixture captures global log output.
Expectations live in `tests/conformance/packs/message_operations/v1.json`.
