import { API_BASE_URL } from "../config";

/**
 * Error thrown when the backend returns 404 for a session-specific endpoint,
 * indicating the session no longer exists or was never created on the backend.
 */
export class SessionNotFoundError extends Error {
  constructor(sessionId: string) {
    super(`Session "${sessionId}" not found on the backend.`);
    this.name = "SessionNotFoundError";
  }
}

/**
 * Generic utility to call chatbot API endpoints.
 *
 * @param endpoint - The path after `/api/chatbot/`
 * @param options - Fetch options like method, headers, body
 * @param fallbackErrorValue - Value to return in case of failure
 * @param timeoutMs - Value of the timeout after which the request is aborted
 * @param throwOnSessionNotFound - If true, throws SessionNotFoundError on 404
 * @returns A Promise resolving to the parsed JSON or fallback value
 */
export const callChatbotApi = async <T>(
  endpoint: string,
  options: RequestInit,
  fallbackErrorValue: T,
  timeoutMs: number,
  throwOnSessionNotFound = false,
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
      // If this is a session endpoint returning 404, throw a specific error
      if (response.status === 404 && throwOnSessionNotFound) {
        // Extract session_id from the endpoint path (e.g., "sessions/{id}/message")
        const match = endpoint.match(/^sessions\/([^/]+)/);
        const sessionId: string = match ? match[1] : "unknown";
        throw new SessionNotFoundError(sessionId);
      }
      console.error(`API error: ${response.status} ${response.statusText}`);
      return fallbackErrorValue;
    }

    return await response.json();
  } catch (error: unknown) {
    if (error instanceof SessionNotFoundError) {
      throw error;
    }
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
