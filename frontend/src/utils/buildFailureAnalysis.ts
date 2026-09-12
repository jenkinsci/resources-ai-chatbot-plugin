export const ANALYZE_BUILD_MESSAGE = "Analyze this Jenkins Build Failure.";
export const ANALYZE_BUILD_INPUT_PREFIX = `${ANALYZE_BUILD_MESSAGE}\n\n`;

export const getConsoleLogContext = (): string => {
  const consoleElement = document.querySelector("pre.console-output");

  return consoleElement?.textContent ?? "";
};

export const removeLogContext = (
  message: string,
  logContext?: string,
): string => (logContext ? message.replace(logContext, "").trim() : message);

export const buildDisplayedMessage = (
  message: string,
  logContext?: string,
): string => {
  const messageWithoutLog = removeLogContext(message, logContext);

  return logContext
    ? `${messageWithoutLog || ANALYZE_BUILD_MESSAGE}\n\n${logContext}`
    : messageWithoutLog;
};
