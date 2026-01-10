import { API_BASE_URL } from "../config";

/**
 * Helper to construct headers with the Jenkins CSRF Crumb if available.
 * This is crucial for POST/PUT/DELETE requests to pass Jenkins security.
 */
const getHeaders = (existingHeaders?: HeadersInit): HeadersInit => {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(existingHeaders as Record<string, string>),
  };

  const jenkinsConfig = window.jenkinsChatbotConfig;

  // If we are in Jenkins, add the Anti-Forgery Token (Crumb)
  if (
    jenkinsConfig &&
    jenkinsConfig.crumbFieldName &&
    jenkinsConfig.crumbToken
  ) {
    headers[jenkinsConfig.crumbFieldName] = jenkinsConfig.crumbToken;
  }

  return headers;
};

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
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);

  const cleanEndpoint = endpoint.startsWith("/")
    ? endpoint.substring(1)
    : endpoint;
  const url = `${API_BASE_URL}/${cleanEndpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: getHeaders(options.headers), // <--- MERGE HEADERS HERE
      signal: controller.signal,
    });

    if (!response.ok) {
      console.error(`API error: ${response.status} ${response.statusText}`);
      return fallbackErrorValue;
    }

    return await response.json();
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name == "AbortError") {
      console.error(
        `API request to ${endpoint} timed out aftr ${timeoutMs}ms.`,
      );
    } else {
      console.error(`API error calling ${endpoint}:`, error);
    }
    return fallbackErrorValue;
  } finally {
    clearTimeout(id);
  }
};
