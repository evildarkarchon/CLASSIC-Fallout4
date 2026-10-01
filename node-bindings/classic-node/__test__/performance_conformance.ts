import * as classic from "../index.js";

type JsonObject = Record<string, any>;

/** Preserve exact millisecond statistics; do not round away adapter unit errors. */
function milliseconds(value: number): number {
    if (!Number.isSafeInteger(value)) throw new Error("metric duration is not an exact integer millisecond");
    return value;
}

/** Convert native whole-nanosecond milliseconds without hiding non-integral drift. */
function nanoseconds(milliseconds: number): number {
    const value = milliseconds * 1e6;
    const rounded = Math.round(value);
    if (!Number.isFinite(value) || value < 0 || Math.abs(value - rounded) > 1e-3) {
        throw new Error("metric duration is not a whole nanosecond");
    }
    return rounded;
}

/** Read the millisecond spelling of a dual-unit fixture sample. */
function sampleMilliseconds(operation: JsonObject): number {
    if (Object.keys(operation).sort().join() !== "label,milliseconds,op,seconds"
        || typeof operation.label !== "string" || typeof operation.milliseconds !== "number") {
        throw new Error("unsupported dual-unit sample");
    }
    return operation.milliseconds;
}

/** Accept only the documented InvalidArg error and return its stable message token. */
function rejectionToken(error: unknown): string {
    const failure = error as Error & {code?: string};
    const separator = failure?.message?.indexOf(": ") ?? -1;
    if (failure?.code !== "InvalidArg" || separator <= 0) throw error;
    return failure.message.slice(0, separator);
}

/** Execute deterministic samples serially and clear process-global state on exit. */
export function observePerformance(fixture: JsonObject): JsonObject {
    if (Object.keys(fixture).join() !== "operations" || !Array.isArray(fixture.operations)) {
        throw new Error("unsupported performance fixture");
    }
    const snapshots: JsonObject[] = [];
    const rejections: string[] = [];
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
            } else if (operation.op === "summaryNs" && keys === "op") {
                snapshots.push(Object.fromEntries(Object.entries(classic.getMetricsSummary().timings).map(([label, stats]) => [label, {
                    count: stats.count, averageNs: nanoseconds(stats.avgMs),
                }])));
            } else if (operation.op === "sample") {
                classic.recordTimingMetric(operation.label, sampleMilliseconds(operation));
            } else if (operation.op === "reject") {
                const milliseconds = sampleMilliseconds(operation);
                let accepted = false;
                try {
                    classic.recordTimingMetric(operation.label, milliseconds);
                    accepted = true;
                } catch (error) {
                    rejections.push(rejectionToken(error));
                }
                if (accepted) throw new Error("invalid sample was accepted");
            } else if (operation.op === "record" && keys === "durationMs,label,op"
                && typeof operation.label === "string" && Number.isSafeInteger(operation.durationMs)
                && operation.durationMs >= 0 && operation.durationMs <= 1000000) {
                classic.recordTimingMetric(operation.label, operation.durationMs);
            } else throw new Error("unsupported performance operation");
        }
        return {snapshots, rejections};
    } finally {
        // Failed scenarios must not contaminate later observations in this serial runner.
        classic.clearAllMetrics();
    }
}
