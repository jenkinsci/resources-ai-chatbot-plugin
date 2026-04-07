import { API_BASE_URL } from "../config";

/**
 * Generic utility to call chatbot API endpoints.
 *
 * @param endpoint - The path after `/api/chatbot/`
 * @param options - Fetch options like method, headers, body
 * @param fallbackErrorValue - Value to return in case of failure
 * @param timeoutMs - Value of the timeout after which the request is aborted
 * @returns A Promise resolving to the parsed JSON or fallback value
 */
export const callChatbotApi = async <T>(
  endpoint: string,
  options: RequestInit,
  fallbackErrorValue: T,
  timeoutMs: number,
): Promise<T> => {
  const callerSignal = options.signal;
  const timeoutSignal = AbortSignal.timeout(timeoutMs);
  const signal = callerSignal
    ? AbortSignal.any([callerSignal, timeoutSignal])
    : timeoutSignal;

  try {
    const response = await fetch(`${API_BASE_URL}/api/chatbot/${endpoint}`, {
      ...options,
      signal,
    });

    if (!response.ok) {
      console.error(`API error: ${response.status} ${response.statusText}`);
      return fallbackErrorValue;
    }

    return await response.json();
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      if (callerSignal?.aborted) {
        console.error("API request cancelled by user");
      } else {
        console.error(
          `API request to ${endpoint} timed out after ${timeoutMs}ms.`,
        );
      }
    } else {
      console.error(`API error calling ${endpoint}:`, error);
    }
    return fallbackErrorValue;
  }
};
