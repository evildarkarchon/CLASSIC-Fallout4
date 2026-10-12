# Minimal BA2 inputs

These are input-only version-1 BA2 archives encoded as JSON byte arrays. The
empty archive has a 24-byte GNRL header. The populated archives contain one
uncompressed chunk and one stored filename, with the filename-stem/directory
CRC values, the format-specific file-header size, and the `0xBAADF00D` chunk
sentinel used by the pinned `ba2` 3.0.1 reader.

GNRL cases contain an MP3 filename or an F4SE script filename. DX10 cases contain
a non-DDS filename or a DDS filename with 7×5 dimensions. Together they exercise
every issue-vector getter with nonempty data; an implementation returning empty
vectors on every scan cannot satisfy the pack. Payload bytes are deliberately
minimal because these scanner operations inspect archive metadata, not audio or
texture decompression.

The `full` and `bridge` inputs contain equivalent archives. Their separate
actions reflect the public surfaces the pack was written for: discovery and
batch scanning (the retired Node and Python bindings), and per-archive vectors
and a summary (CXX). Expected results
remain authored in the scenario pack and never enter native run plans.
