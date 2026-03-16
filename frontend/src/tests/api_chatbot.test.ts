import {
  createBotMessage,
  createChatSession,
  deleteChatSession,
  sendMessage,
} from "../api/chatbot";

import { callChatbotApi } from "../utils/callChatbotApi";
import { getChatbotText } from "../data/chatbotTexts";
import { API_BASE_URL, CHATBOT_API_TIMEOUTS_MS } from "../config";

jest.mock("uuid", () => ({
  v4: () => "mock-uuid",
}));

jest.mock("../utils/callChatbotApi", () => ({
  callChatbotApi: jest.fn(),
}));

jest.mock("../data/chatbotTexts", () => ({
  getChatbotText: jest.fn().mockReturnValue("Fallback error message"),
}));

// Mock global fetch for the sendMessage function tests
global.fetch = jest.fn();

describe("chatbotApi", () => {
  beforeEach(() => {
    (callChatbotApi as jest.Mock).mockClear();
    (global.fetch as jest.Mock).mockClear();
    (getChatbotText as jest.Mock).mockClear();
  });

  describe("createBotMessage", () => {
    it("creates a bot message with text", () => {
      const message = createBotMessage("Hello world");
      expect(message).toEqual({
        id: "mock-uuid",
        sender: "jenkins-bot",
        text: "Hello world",
      });
    });
  });

  describe("createChatSession", () => {
    it("creates a session and returns the session id", async () => {
      (callChatbotApi as jest.Mock).mockResolvedValueOnce({
        session_id: "abc123",
      });
      const result = await createChatSession();
      expect(result).toBe("abc123");
      expect(callChatbotApi).toHaveBeenCalledWith(
        "sessions",
        { method: "POST" },
        { session_id: "" },
        expect.any(Number),
      );
    });

    it("returns empty result if session_id is missing in response", async () => {
      (callChatbotApi as jest.Mock).mockResolvedValueOnce({});
      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();
      const result = await createChatSession();
      expect(result).toBe("");
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to create chat session: session_id missing in response",
        {},
      );
      consoleErrorSpy.mockRestore();
    });
  });

  describe("sendMessage", () => {
    beforeEach(() => {
      jest.useFakeTimers();
      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: jest.fn().mockResolvedValue({ reply: "Success" }),
      } as unknown as Response);
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it("sends a text-only message", async () => {
      const result = await sendMessage("session-123", "Hello world");
      expect(global.fetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/chatbot/sessions/session-123/message`,
        expect.any(Object),
      );
      const fetchOptions = (global.fetch as jest.Mock).mock.calls[0][1];
      expect(fetchOptions.method).toBe("POST");
      const formData = fetchOptions.body as FormData;
      expect(formData.get("message")).toBe("Hello world");
      expect(formData.has("files")).toBe(false);
      expect(result.text).toBe("Success");
    });

    it("sends a message with files", async () => {
      const file = new File(["content"], "test.txt");
      await sendMessage("session-123", "Check file", [file]);
      const fetchOptions = (global.fetch as jest.Mock).mock.calls[0][1];
      const formData = fetchOptions.body as FormData;
      expect(formData.get("message")).toBe("Check file");
      expect(formData.get("files")).toBe(file);
    });

    it("sends a file-only message", async () => {
      const file = new File(["content"], "test.txt");
      await sendMessage("session-123", undefined, [file]);
      const fetchOptions = (global.fetch as jest.Mock).mock.calls[0][1];
      const formData = fetchOptions.body as FormData;
      expect(formData.has("message")).toBe(false);
      expect(formData.get("files")).toBe(file);
    });

    it("returns fallback message on API error", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: "Server Error" }),
      });
      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();
      const result = await sendMessage("session-123", "Hi");
      expect(result.text).toBe("Fallback error message");
      expect(getChatbotText).toHaveBeenCalledWith("errorMessage");
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "API error: 500 - Server Error",
      );
      consoleErrorSpy.mockRestore();
    });

    it("returns an empty message on user cancellation", async () => {
      (global.fetch as jest.Mock).mockImplementation(
        (_url, options) =>
          new Promise((_, reject) =>
            options?.signal?.addEventListener("abort", () =>
              reject(new DOMException("Aborted", "AbortError")),
            ),
          ),
      );
      const controller = new AbortController();
      const promise = sendMessage(
        "session-123",
        "Hi",
        undefined,
        controller.signal,
      );
      controller.abort();
      const result = await promise;
      expect(result.text).toBe("");
    });

    it("handles timeout", async () => {
      (global.fetch as jest.Mock).mockImplementation(
        () => new Promise(() => {}), // Never resolves
      );
      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();
      const promise = sendMessage("session-123", "Hi");
      jest.advanceTimersByTime(CHATBOT_API_TIMEOUTS_MS.GENERATE_MESSAGE);
      const result = await promise;
      expect(result.text).toBe("Fallback error message");
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        `API request timed out after ${CHATBOT_API_TIMEOUTS_MS.GENERATE_MESSAGE}ms`,
      );
      consoleErrorSpy.mockRestore();
    });
  });

  describe("deleteChatSession", () => {
    it("calls callChatbotApi with DELETE method", async () => {
      (callChatbotApi as jest.Mock).mockResolvedValueOnce(undefined);
      await deleteChatSession("session-xyz");
      expect(callChatbotApi).toHaveBeenCalledWith(
        "sessions/session-xyz",
        { method: "DELETE" },
        undefined,
        expect.any(Number),
      );
    });
  });
});
