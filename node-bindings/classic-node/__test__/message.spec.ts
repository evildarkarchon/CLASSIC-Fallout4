import { describe, test, expect } from "bun:test";
import {
  createMessage,
  formatMessage,
  createLogger,
  JsLogger,
  JsMessageType,
  JsMessageTarget,
} from "../index.js";

describe("Message enums", () => {
  test("JsMessageType enum values are correct strings", () => {
    expect(JsMessageType.Info).toBe("Info");
    expect(JsMessageType.Warning).toBe("Warning");
    expect(JsMessageType.Error).toBe("Error");
    expect(JsMessageType.Success).toBe("Success");
    expect(JsMessageType.Progress).toBe("Progress");
    expect(JsMessageType.Debug).toBe("Debug");
    expect(JsMessageType.Critical).toBe("Critical");
  });

  test("JsMessageTarget enum values are correct strings", () => {
    expect(JsMessageTarget.All).toBe("All");
    expect(JsMessageTarget.Gui).toBe("Gui");
    expect(JsMessageTarget.Console).toBe("Console");
    expect(JsMessageTarget.LogOnly).toBe("LogOnly");
  });
});

describe("createMessage", () => {
  test("creates a valid message with default target", () => {
    const msg = createMessage(JsMessageType.Info, "Hello world");
    expect(msg).toBeDefined();
    expect(msg.messageType).toBe("Info");
    expect(msg.target).toBe("All");
    expect(msg.content).toBe("Hello world");
    expect(msg.title).toBeUndefined();
    expect(msg.details).toBeUndefined();
    expect(typeof msg.timestamp).toBe("number");
    expect(msg.timestamp).toBeGreaterThan(0);
  });

  test("creates a message with explicit Gui target", () => {
    const msg = createMessage(
      JsMessageType.Warning,
      "GUI warning",
      JsMessageTarget.Gui,
    );
    expect(msg.messageType).toBe("Warning");
    expect(msg.target).toBe("Gui");
    expect(msg.content).toBe("GUI warning");
  });

  test("creates a message with LogOnly target", () => {
    const msg = createMessage(
      JsMessageType.Debug,
      "debug info",
      JsMessageTarget.LogOnly,
    );
    expect(msg.target).toBe("LogOnly");
  });

  test("creates an error message", () => {
    const msg = createMessage(JsMessageType.Error, "Something failed");
    expect(msg.messageType).toBe("Error");
    expect(msg.content).toBe("Something failed");
  });

  test("creates all message types", () => {
    const types = [
      JsMessageType.Info,
      JsMessageType.Warning,
      JsMessageType.Error,
      JsMessageType.Success,
      JsMessageType.Progress,
      JsMessageType.Debug,
      JsMessageType.Critical,
    ];
    for (const t of types) {
      const msg = createMessage(t, `test-${t}`);
      expect(msg.messageType).toBe(t);
    }
  });
});

describe("formatMessage", () => {
  test("preserves emojis in message content", () => {
    const msg = createMessage(JsMessageType.Success, "Done! ✅");
    const formatted = formatMessage(msg);
    expect(formatted).toBe("Done! ✅");
  });

  test("formats message without details", () => {
    const msg = {
      messageType: "Info",
      target: "All",
      content: "Plain text",
      title: undefined,
      details: undefined,
      timestamp: Date.now(),
    };
    const formatted = formatMessage(msg);
    expect(formatted).toBe("Plain text");
  });

  test("formats message with details", () => {
    const msg = {
      messageType: "Error",
      target: "All",
      content: "Error occurred",
      title: undefined,
      details: "Stack trace here",
      timestamp: Date.now(),
    };
    const formatted = formatMessage(msg);
    expect(formatted).toContain("Error occurred");
    expect(formatted).toContain("Details:");
    expect(formatted).toContain("Stack trace here");
  });

  test("preserves emojis in content and details", () => {
    const msg = {
      messageType: "Success",
      target: "All",
      content: "Success! 🎉",
      title: undefined,
      details: "All tests passed ✅",
      timestamp: Date.now(),
    };
    const formatted = formatMessage(msg);
    expect(formatted).toBe("Success! 🎉\nDetails: All tests passed ✅");
  });
});

describe("JsLogger", () => {
  test("creates a logger via constructor", () => {
    const logger = new JsLogger("test-logger");
    expect(logger).toBeDefined();
    expect(logger.name).toBe("test-logger");
  });

  test("creates a logger via factory function", () => {
    const logger = createLogger("factory-logger");
    expect(logger).toBeDefined();
    expect(logger.name).toBe("factory-logger");
  });

  test("logger has all logging methods", () => {
    const logger = new JsLogger("method-test");
    expect(typeof logger.info).toBe("function");
    expect(typeof logger.warning).toBe("function");
    expect(typeof logger.error).toBe("function");
    expect(typeof logger.debug).toBe("function");
  });

  test("logging methods do not throw", () => {
    const logger = new JsLogger("safe-logger");
    expect(() => logger.info("info message")).not.toThrow();
    expect(() => logger.warning("warning message")).not.toThrow();
    expect(() => logger.error("error message")).not.toThrow();
    expect(() => logger.debug("debug message")).not.toThrow();
  });
});
