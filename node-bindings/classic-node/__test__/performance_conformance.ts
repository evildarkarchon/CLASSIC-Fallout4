import * as classic from "../index.js";

type JsonObject = Record<string, any>;

/** Preserve exact millisecond statistics; do not round away adapter unit errors. */
function milliseconds(value: number): number {
  if (!Number.isSafeInteger(value)) throw new Error("metric duration is not an exact integer millisecond");
  return value;
}

/** Execute deterministic samples serially and clear process-global state on exit. */
export function observePerformance(fixture: JsonObject): JsonObject {
  if (Object.keys(fixture).join() !== "operations" || !Array.isArray(fixture.operations)) {
    throw new Error("unsupported performance fixture");
  }
  const snapshots: JsonObject[] = [];
  classic.clearAllMetrics();
  try {
    for (const operation of fixture.operations) {
      const keys = Object.keys(operation).sort().join();
      if (operation.op === "clear" && keys === "op") {
        classic.clearAllMetrics();
      } else if (operation.op === "summary" && keys === "op") {
        snapshots.push(Object.fromEntries(Object.entries(classic.getMetricsSummary().timings).map(([label, stats]) => [label, {
          count: stats.count, totalMs: milliseconds(stats.totalMs), averageMs: milliseconds(stats.avgMs),
          minMs: milliseconds(stats.minMs), maxMs: milliseconds(stats.maxMs),
        }])));
      } else if (operation.op === "record" && keys === "durationMs,label,op"
          && typeof operation.label === "string" && Number.isSafeInteger(operation.durationMs)
          && operation.durationMs >= 0 && operation.durationMs <= 1000000) {
        classic.recordTimingMetric(operation.label, operation.durationMs);
      } else throw new Error("unsupported performance operation");
    }
    return { snapshots };
  } finally {
    // Failed scenarios must not contaminate later observations in this serial runner.
    classic.clearAllMetrics();
  }
}
