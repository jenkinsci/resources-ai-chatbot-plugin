import {
  ANALYZE_BUILD_MESSAGE,
  ANALYZE_BUILD_INPUT_PREFIX,
  getConsoleLogContext,
  removeLogContext,
  buildDisplayedMessage,
} from "../utils/buildFailureAnalysis";

describe("buildFailureAnalysis utils", () => {
  describe("constants", () => {
    it("has the correct constant message values", () => {
      expect(ANALYZE_BUILD_MESSAGE).toBe("Analyze this Jenkins Build Failure.");
      expect(ANALYZE_BUILD_INPUT_PREFIX).toBe(
        "Analyze this Jenkins Build Failure.\n\n",
      );
    });
  });

  describe("getConsoleLogContext", () => {
    afterEach(() => {
      document.body.innerHTML = "";
    });

    it("returns text content when pre.console-output element is present", () => {
      const pre = document.createElement("pre");
      pre.className = "console-output";
      pre.textContent = "BUILD FAILED: compilation error";
      document.body.appendChild(pre);

      expect(getConsoleLogContext()).toBe("BUILD FAILED: compilation error");
    });

    it("returns empty string when pre.console-output is not present", () => {
      expect(getConsoleLogContext()).toBe("");
    });

    it("returns empty string when pre.console-output has null textContent", () => {
      const pre = document.createElement("pre");
      pre.className = "console-output";
      jest
        .spyOn(pre, "textContent", "get")
        .mockReturnValue(null as unknown as string);
      document.body.appendChild(pre);

      expect(getConsoleLogContext()).toBe("");
    });
  });

  describe("removeLogContext", () => {
    it("removes log context from message and trims remaining whitespace", () => {
      const message = "Please check this error: \nStack trace line 1";
      const logContext = "Stack trace line 1";
      expect(removeLogContext(message, logContext)).toBe(
        "Please check this error:",
      );
    });

    it("returns the original message if logContext is undefined or empty", () => {
      expect(removeLogContext("Hello world")).toBe("Hello world");
      expect(removeLogContext("Hello world", undefined)).toBe("Hello world");
      expect(removeLogContext("Hello world", "")).toBe("Hello world");
    });
  });

  describe("buildDisplayedMessage", () => {
    it("returns message without log when logContext is missing or empty", () => {
      expect(buildDisplayedMessage("Check this issue")).toBe(
        "Check this issue",
      );
      expect(buildDisplayedMessage("Check this issue", "")).toBe(
        "Check this issue",
      );
    });

    it("formats message with logContext when message has additional text", () => {
      const log = "FATAL: OutOfMemoryError";
      const fullMessage = `What happened?\n\n${log}`;
      const result = buildDisplayedMessage(fullMessage, log);
      expect(result).toBe(`What happened?\n\n${log}`);
    });

    it("falls back to ANALYZE_BUILD_MESSAGE when message becomes empty after removing logContext", () => {
      const log = "FATAL: OutOfMemoryError";
      const result = buildDisplayedMessage(log, log);
      expect(result).toBe(`${ANALYZE_BUILD_MESSAGE}\n\n${log}`);
    });
  });
});
