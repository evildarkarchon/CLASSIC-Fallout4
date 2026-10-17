# Settings validation fixtures

Input-only cases call public validation and coercion for every supported type.
Observations retain actual booleans, scalar values, and native coercion errors.
The family covers false booleans, empty strings, empty paths, invalid booleans
and invalid integers. The Rust participant runs it; CXX does not enrol it.

Receipt JSON forbids floating-point numbers. Float results use an explicit
`{"float": "3.125e0"}` carrier preserving the numeric type and value.

Float carriers use shortest-round-trip scientific digits with an unpadded integer
exponent. The precision fixture includes 1.23456789, large and small exponents,
an integral float and negative zero so transport cannot hide precision loss.
