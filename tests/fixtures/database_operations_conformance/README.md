# Database pool fixtures

These input-only fixtures exercise `classic-database-core::DatabasePool` through
Rust, CXX, Node, and Python. Adapters write the supplied lowercase SQLite hex to a
disposable `formids.db`, invoke public operations, close every pool, then re-read
every durable file byte. Missing input remains absent; invalid input is attributed
to the native open error carrier and remains byte-identical.

`populated.json` holds a 512-byte-page SQLite database created with:

```sql
CREATE TABLE Fallout4(formid TEXT NOT NULL, plugin TEXT NOT NULL, entry TEXT NOT NULL);
INSERT INTO Fallout4 VALUES ('000001', 'Example.esp', 'Alpha café');
INSERT INTO Fallout4 VALUES ('000002', 'Example.esp', '');
```

The query sequence exercises plugin case fallback, an empty-string hit, a miss,
and a repeated lookup. Single and batch results preserve input order and the
difference between empty and absent values. CXX additionally compares legacy
sentinels and hit-only tab-delimited batches with typed result flags and identity.
Cache clearing and closed availability are observed through public operations.

The committed database bytes are fixture inputs, never adapter-created expected
results. Expectations live only in the scenario pack. Existing tests retain
statistics, cache policy tuning, optimizer/rebalance behavior, concurrency, and
strict FormID lookup coverage; this pack does not grant evidence for those APIs.
