import {
  createBotMessage,
  createChatSession,
  fetchChatbotReply,
  deleteChatSession,
  fetchChatbotReplyWithFiles,
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

// Mock global fetch for file upload tests
global.fetch = jest.fn();

describe("chatbotApi", () => {
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

  describe("fetchChatbotReply", () => {
    it("returns a bot message when API reply is present", async () => {
      (callChatbotApi as jest.Mock).mockResolvedValueOnce({
        reply: "Hello from bot!",
      });

      const result = await fetchChatbotReply("session-xyz", "Hi!");

      expect(result).toEqual({
        id: "mock-uuid",
        sender: "jenkins-bot",
        text: "Hello from bot!",
      });

      expect(callChatbotApi).toHaveBeenCalledWith(
        "sessions/session-xyz/message",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: "Hi!" }),
        },
        {},
        expect.any(Number),
      );
    });

    it("uses fallback error message when API reply is missing", async () => {
      (callChatbotApi as jest.Mock).mockResolvedValueOnce({});

      const result = await fetchChatbotReply("session-xyz", "Hi!");

      expect(getChatbotText).toHaveBeenCalledWith("errorMessage");

      expect(result).toEqual({
        id: "mock-uuid",
        sender: "jenkins-bot",
        text: "Fallback error message",
      });
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

    it("does not throw when callChatbotApi returns undefined", async () => {
      (callChatbotApi as jest.Mock).mockResolvedValueOnce(undefined);

      await expect(deleteChatSession("session-fail")).resolves.toBeUndefined();

      expect(callChatbotApi).toHaveBeenCalledWith(
        "sessions/session-fail",
        { method: "DELETE" },
        undefined,
        expect.any(Number),
      );
    });
  });

  describe("fetchChatbotReplyWithFiles", () => {
    beforeEach(() => {
      jest.clearAllMocks();
      (global.fetch as jest.Mock).mockClear();
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it("successfully uploads files and returns bot reply", async () => {
      const mockResponse = {
        reply: "File analyzed successfully!",
      };
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const files = [
        new File(["content"], "test.txt", { type: "text/plain" }),
      ];
      const controller = new AbortController();

      const result = await fetchChatbotReplyWithFiles(
        "session-xyz",
        "Analyze this file",
        files,
        controller.signal,
      );

      expect(result).toEqual({
        id: "mock-uuid",
        sender: "jenkins-bot",
        text: "File analyzed successfully!",
      });

      expect(global.fetch).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/chatbot/sessions/session-xyz/message/upload`,
        expect.objectContaining({
          method: "POST",
          signal: expect.any(AbortSignal),
        }),
      );
    });

    it("returns fallback message when API response is not ok", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: "Internal server error" }),
      });

      const files = [
        new File(["content"], "test.txt", { type: "text/plain" }),
      ];
      const controller = new AbortController();
      const consoleErrorSpy = jest
        .spyOn(console, "error")
        .mockImplementation();

      const result = await fetchChatbotReplyWithFiles(
        "session-xyz",
        "Hello",
        files,
        controller.signal,
      );

      expect(result.text).toBe("Fallback error message");
      expect(consoleErrorSpy).toHaveBeenCalled();
      consoleErrorSpy.mockRestore();
    });

    it("aborts the request when timeout elapses", async () => {
      // Mock fetch to reject with AbortError when signal is aborted
      (global.fetch as jest.Mock).mockImplementationOnce(
        (url: string, options?: RequestInit) => {
          return new Promise((_, reject) => {
            // Reject with AbortError when signal is aborted
            if (options?.signal) {
              options.signal.addEventListener("abort", () => {
                const error = new DOMException("Aborted", "AbortError");
                reject(error);
              });
            }
          }) as unknown as Promise<Response>;
        },
      );

      const files = [
        new File(["content"], "test.txt", { type: "text/plain" }),
      ];
      const controller = new AbortController();
      const consoleErrorSpy = jest
        .spyOn(console, "error")
        .mockImplementation();

      const promise = fetchChatbotReplyWithFiles(
        "session-xyz",
        "Hello",
        files,
        controller.signal,
      );

      // Fast-forward time to trigger timeout
      jest.advanceTimersByTime(CHATBOT_API_TIMEOUTS_MS.GENERATE_MESSAGE);

      // Wait for promise to resolve after timeout
      const result = await promise;

      expect(result.text).toBe("Fallback error message");
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        expect.stringContaining("timed out"),
      );
      consoleErrorSpy.mockRestore();
    });

    it("cancels the request when external signal is aborted", async () => {
      // Mock fetch to hang indefinitely
      (global.fetch as jest.Mock).mockImplementationOnce(
        () =>
          new Promise(() => {
            // Never resolves
          }) as unknown as Promise<Response>,
      );

      const files = [
        new File(["content"], "test.txt", { type: "text/plain" }),
      ];
      const controller = new AbortController();
      const consoleErrorSpy = jest
        .spyOn(console, "error")
        .mockImplementation();

      const promise = fetchChatbotReplyWithFiles(
        "session-xyz",
        "Hello",
        files,
        controller.signal,
      );

      // Abort the external signal (simulating user clicking Cancel)
      controller.abort();

      const result = await promise;

      expect(result.text).toBe("Fallback error message");
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "API request cancelled by user",
      );
      consoleErrorSpy.mockRestore();
    });

    it("handles already aborted external signal", async () => {
      const files = [
        new File(["content"], "test.txt", { type: "text/plain" }),
      ];
      const controller = new AbortController();
      controller.abort(); // Abort before calling the function

      const consoleErrorSpy = jest
        .spyOn(console, "error")
        .mockImplementation();

      const result = await fetchChatbotReplyWithFiles(
        "session-xyz",
        "Hello",
        files,
        controller.signal,
      );

      expect(result.text).toBe("Fallback error message");
      expect(consoleErrorSpy).toHaveBeenCalled();
      consoleErrorSpy.mockRestore();
    });

    it("handles network errors gracefully", async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(
        new Error("Network error"),
      );

      const files = [
        new File(["content"], "test.txt", { type: "text/plain" }),
      ];
      const controller = new AbortController();
      const consoleErrorSpy = jest
        .spyOn(console, "error")
        .mockImplementation();

      const result = await fetchChatbotReplyWithFiles(
        "session-xyz",
        "Hello",
        files,
        controller.signal,
      );

      expect(result.text).toBe("Fallback error message");
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "API error uploading files:",
        expect.any(Error),
      );
      consoleErrorSpy.mockRestore();
    });

    it("creates FormData with message and files correctly", async () => {
      const mockResponse = {
        reply: "Success",
      };
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const files = [
        new File(["content1"], "file1.txt", { type: "text/plain" }),
        new File(["content2"], "file2.txt", { type: "text/plain" }),
      ];
      const controller = new AbortController();

      await fetchChatbotReplyWithFiles(
        "session-xyz",
        "Test message",
        files,
        controller.signal,
      );

      const fetchCall = (global.fetch as jest.Mock).mock.calls[0];
      expect(fetchCall[1]?.body).toBeInstanceOf(FormData);
    });
  });
});
