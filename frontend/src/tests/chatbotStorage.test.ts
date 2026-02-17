import {
  loadChatbotSessions,
  loadChatbotLastSessionId,
} from "../utils/chatbotStorage";
import { type ChatSession } from "../model/ChatSession";

describe("storageUtils", () => {
  const mockSessions: ChatSession[] = [
    {
      id: "session-1",
      messages: [],
      createdAt: "2024-01-01T00:00:00Z",
      isLoading: false,
      loadingStatus: null,
    },
    {
      id: "session-2",
      messages: [],
      createdAt: "2024-01-02T00:00:00Z",
      isLoading: false,
      loadingStatus: null,
    },
  ];

  beforeEach(() => {
    sessionStorage.clear();
    jest.clearAllMocks();
  });

  describe("loadChatbotSessions", () => {
    it("returns parsed sessions when data exists and is valid", () => {
      sessionStorage.setItem("chatbot-sessions", JSON.stringify(mockSessions));
      const result = loadChatbotSessions();
      expect(result).toEqual(mockSessions);
    });

    it("returns empty array when no data exists", () => {
      const result = loadChatbotSessions();
      expect(result).toEqual([]);
    });

    it("returns empty array when data is invalid JSON", () => {
      sessionStorage.setItem("chatbot-sessions", "not-json");
      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();
      const result = loadChatbotSessions();
      expect(result).toEqual([]);
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to parse saved chat sessions",
        expect.any(SyntaxError),
      );
    });

    it("returns empty array if the session has an invalid shape", () => {
      const invalidSessions = JSON.stringify([
        {
          id: "bad-session",
          messages: "invalid-object-structure",
          createdAt: "2024-01-01T00:00:00Z",
          isLoading: true,
        },
      ]);

      sessionStorage.setItem("chatbot-sessions", invalidSessions);

      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();
      const result = loadChatbotSessions();

      expect(result).toEqual([]);
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Invalid chat session data structure:",
        expect.anything(),
      );

      consoleErrorSpy.mockRestore();
    });

    it("returns empty array when saved data is an empty string", () => {
      sessionStorage.setItem("chatbot-sessions", "");
      const result = loadChatbotSessions();
      expect(result).toEqual([]);
    });

    it("returns empty array when saved data is an empty array", () => {
      sessionStorage.setItem("chatbot-sessions", "[]");
      const result = loadChatbotSessions();
      expect(result).toEqual([]);
    });
  });

  describe("loadChatbotLastSessionId", () => {
    it("returns the last session ID if it exists and matches a session", () => {
      sessionStorage.setItem("chatbot-sessions", JSON.stringify(mockSessions));
      sessionStorage.setItem("chatbot-last-session-id", "session-2");
      const result = loadChatbotLastSessionId();
      expect(result).toBe("session-2");
    });

    it("returns the first session ID if the last session ID does not match", () => {
      const consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation();
      sessionStorage.setItem("chatbot-sessions", JSON.stringify(mockSessions));
      sessionStorage.setItem("chatbot-last-session-id", "non-existent-id");
      const result = loadChatbotLastSessionId();
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        "No last session id found: setting the current session to the first item.",
      );
      expect(result).toBe("session-1");
    });

    it("returns the first session ID if no last session ID is stored", () => {
      const consoleWarnSpy = jest.spyOn(console, "warn").mockImplementation();
      sessionStorage.setItem("chatbot-sessions", JSON.stringify(mockSessions));
      const result = loadChatbotLastSessionId();
      expect(consoleWarnSpy).toHaveBeenCalled();
      expect(result).toBe("session-1");
    });

    it("returns null if no sessions exist", () => {
      const result = loadChatbotLastSessionId();
      expect(result).toBeNull();
    });
  });
});
