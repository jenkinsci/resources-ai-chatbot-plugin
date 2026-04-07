import { type ChatSession, isChatSession } from "../model/ChatSession";

/**
 * Loads the saved chatbot sessions from sessionStorage.
 *
 * This function attempts to retrieve and parse the serialized chat sessions
 * stored under the 'chatbot-sessions' key in sessionStorage.
 * If the data is invalid, not present, or contains invalid session objects, it returns an empty array.
 *
 * @returns {ChatSession[]} An array of chat sessions, or an empty array if none are found or parsing fails.
 */
export const loadChatbotSessions = (): ChatSession[] => {
  const saved = sessionStorage.getItem("chatbot-sessions");
  if (saved && saved.length > 0) {
    try {
      const parsed = JSON.parse(saved);

      if (Array.isArray(parsed) && parsed.every(isChatSession)) {
        return parsed;
      } else {
        console.error("Invalid chat session data structure:", parsed);
      }
    } catch (e) {
      console.error("Failed to parse saved chat sessions", e);
    }
  }
  return [];
};

/**
 * Retrieves the ID of the last active chatbot session from sessionStorage.
 *
 * This function reads the 'chatbot-last-session-id' value and validates that it
 * corresponds to an existing session. If it's valid, the ID is returned.
 * If not, it returns the ID of the first available session as a fallback.
 * Returns null if no sessions are stored.
 *
 * @returns {string | null} The last active session ID, the first available session ID, or null if no sessions exist.
 */
export const loadChatbotLastSessionId = (): string | null => {
  const sessions: ChatSession[] = loadChatbotSessions();
  if (sessions && sessions.length > 0) {
    const lastSessionId = sessionStorage.getItem("chatbot-last-session-id");

    if (
      lastSessionId &&
      sessions.find((session) => session.id === lastSessionId)
    ) {
      return lastSessionId;
    }
    console.warn(
      "No last session id found: setting the current session to the first item.",
    );
    return sessions[0].id;
  }

  return null;
};
