import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import * as classic from "../index";

/** Capture actual native records from a fresh process with an explicitly initialized logger. */
export function observeMessageLogging(fixture: Record<string, any>): Record<string, any> {
  const child = spawnSync(process.execPath, [fileURLToPath(import.meta.url), "--worker", JSON.stringify(fixture)], {
    encoding: "utf8", env: { ...process.env, RUST_LOG: "trace", RUST_LOG_STYLE: "never" },
  });
  if (child.status !== 0) throw new Error(`Native logging worker failed: ${child.stderr}`);
  const records = child.stderr.trim().split(/\r?\n/).filter(Boolean).map(line => {
    const match = /^\[[^\]]+\s(TRACE|DEBUG|INFO|WARN|ERROR)\s+[^\]]+\] (.*)$/.exec(line);
    if (!match) throw new Error(`Unrecognized native log record: ${line}`);
    return { level: match[1], message: match[2] };
  });
  return { records, ...JSON.parse(child.stdout) };
}

if (process.argv[2] === "--worker") {
  const fixture = JSON.parse(process.argv[3]);
  if (fixture.operation !== "basic") throw new Error("Unsupported Node logging operation");
  classic.initLogging();
  classic.initLogging();
  const logger = new classic.JsLogger(fixture.name);
  const factory = classic.createLogger(fixture.name);
  if (logger.name !== fixture.name || factory.name !== logger.name) throw new Error("Logger names disagree");
  logger.info(fixture.messages.info);
  factory.warning(fixture.messages.warning);
  logger.error(fixture.messages.error);
  factory.debug(fixture.messages.debug);
  process.stdout.write("{}");
}
