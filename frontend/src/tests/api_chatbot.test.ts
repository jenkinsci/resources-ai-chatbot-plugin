import {
  createBotMessage,
  createChatSession,
  fetchChatbotReply,
  deleteChatSession,
  streamChatbotReply,
  fetchChatbotReplyWithFiles,
} from "../api/chatbot";

import { callChatbotApi } from "../utils/callChatbotApi";
import { getChatbotText } from "../data/chatbotTexts";
import { WS } from "jest-websocket-mock";
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

import fetchMock from "jest-fetch-mock";

// Mock global fetch for file upload tests
fetchMock.enableMocks();

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

  describe("streamChatbotReply", () => {
    let server: WS;
    const sessionId = "test-session-123";
    const userMessage = "Hello, bot!";

    beforeEach(() => {
      // Create a new WebSocket server for each test
      server = new WS(
        `ws://localhost:8000/api/chatbot/sessions/${sessionId}/stream`,
      );
    });

    afterEach(() => {
      WS.clean();
    });

    it("establishes WebSocket connection successfully", async () => {
      const onToken = jest.fn();
      const onComplete = jest.fn();
      const onError = jest.fn();

      const ws = streamChatbotReply(
        sessionId,
        userMessage,
        onToken,
        onComplete,
        onError,
      );

      expect(ws).not.toBeNull();
      await server.connected;
      // Wait for onopen handler to execute and send message
      await new Promise((resolve) => setTimeout(resolve, 10));
      expect(server).toHaveReceivedMessages([
        JSON.stringify({ message: userMessage }),
      ]);
    });

    it("streams tokens correctly", async () => {
      const tokens: string[] = [];
      const onToken = jest.fn((token: string) => {
        tokens.push(token);
      });
      const onComplete = jest.fn();
      const onError = jest.fn();

      streamChatbotReply(sessionId, userMessage, onToken, onComplete, onError);

      await server.connected;
      await server.nextMessage; // Wait for initial message

      // Simulate token streaming
      server.send(JSON.stringify({ token: "Hello" }));
      server.send(JSON.stringify({ token: " " }));
      server.send(JSON.stringify({ token: "world" }));

      // Wait for messages to be processed
      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(onToken).toHaveBeenCalledTimes(3);
      expect(onToken).toHaveBeenCalledWith("Hello");
      expect(onToken).toHaveBeenCalledWith(" ");
      expect(onToken).toHaveBeenCalledWith("world");
      expect(tokens.join("")).toBe("Hello world");
    });

    it("calls onComplete when receiving {end: true}", async () => {
      const onToken = jest.fn();
      const onComplete = jest.fn();
      const onError = jest.fn();

      streamChatbotReply(sessionId, userMessage, onToken, onComplete, onError);

      await server.connected;
      await server.nextMessage;

      server.send(JSON.stringify({ token: "Hello" }));
      server.send(JSON.stringify({ end: true }));

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(onComplete).toHaveBeenCalledTimes(1);
      expect(onError).not.toHaveBeenCalled();
    });

    it("handles error messages from backend", async () => {
      const onToken = jest.fn();
      const onComplete = jest.fn();
      const onError = jest.fn();

      streamChatbotReply(sessionId, userMessage, onToken, onComplete, onError);

      await server.connected;
      await server.nextMessage;

      const errorMessage = "Session not found";
      server.send(JSON.stringify({ error: errorMessage }));

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(onError).toHaveBeenCalledTimes(1);
      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: errorMessage,
        }),
      );
      expect(onToken).not.toHaveBeenCalled();
      expect(onComplete).not.toHaveBeenCalled();
    });

    it("handles connection failure and calls onError", async () => {
      const onToken = jest.fn();
      const onComplete = jest.fn();
      const onError = jest.fn();

      // Close server before connection attempt
      server.close();

      const ws = streamChatbotReply(
        sessionId,
        userMessage,
        onToken,
        onComplete,
        onError,
      );

      // Wait for connection attempt to fail
      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(ws).not.toBeNull();
      // Error should be called when connection fails
      expect(onError).toHaveBeenCalled();
    });

    it("returns null and calls onError when WebSocket is not supported", () => {
      // Mock WebSocket as undefined
      const originalWebSocket = globalThis.WebSocket;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (globalThis as any).WebSocket = undefined;

      const onToken = jest.fn();
      const onComplete = jest.fn();
      const onError = jest.fn();

      const ws = streamChatbotReply(
        sessionId,
        userMessage,
        onToken,
        onComplete,
        onError,
      );

      expect(ws).toBeNull();
      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: expect.stringContaining("WebSocket is not supported"),
        }),
      );

      // Restore WebSocket
      globalThis.WebSocket = originalWebSocket;
    });

    it("handles malformed JSON messages gracefully", async () => {
      const onToken = jest.fn();
      const onComplete = jest.fn();
      const onError = jest.fn();

      streamChatbotReply(sessionId, userMessage, onToken, onComplete, onError);

      await server.connected;
      await server.nextMessage;

      // Send invalid JSON
      server.send("not valid json");

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(onError).toHaveBeenCalled();
      expect(onError.mock.calls[0][0].message).toContain(
        "Failed to parse WebSocket message",
      );
    });
  });

  describe("fetchChatbotReplyWithFiles", () => {
    beforeEach(() => {
      jest.clearAllMocks();
      fetchMock.mockClear();
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it("successfully uploads files and returns bot reply", async () => {
      const mockResponse = {
        reply: "File analyzed successfully!",
      };
      fetchMock.mockResponseOnce(JSON.stringify(mockResponse));

      const files = [new File(["content"], "test.txt", { type: "text/plain" })];
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

      expect(fetchMock).toHaveBeenCalledWith(
        `${API_BASE_URL}/api/chatbot/sessions/session-xyz/message/upload`,
        expect.objectContaining({
          method: "POST",
          signal: expect.any(AbortSignal),
        }),
      );
    });

    it("returns fallback message when API response is not ok", async () => {
      fetchMock.mockResponseOnce(
        JSON.stringify({ detail: "Internal server error" }),
        {
          status: 500,
        },
      );

      const files = [new File(["content"], "test.txt", { type: "text/plain" })];
      const controller = new AbortController();
      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();

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
      fetchMock.mockImplementationOnce(
        (_url: string | Request | undefined, options?: RequestInit) =>
          new Promise((_, reject) => {
            // Reject with AbortError when signal is aborted
            if (options?.signal) {
              options.signal.addEventListener("abort", () => {
                const error = new DOMException("Aborted", "AbortError");
                reject(error);
              });
            }
          }) as unknown as Promise<Response>,
      );

      const files = [new File(["content"], "test.txt", { type: "text/plain" })];
      const controller = new AbortController();
      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();

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
      // Mock fetch to reject when signal is aborted
      fetchMock.mockImplementationOnce(
        (_url: string | Request | undefined, options?: RequestInit) =>
          new Promise((_, reject) => {
            if (options?.signal) {
              options.signal.addEventListener("abort", () => {
                reject(new DOMException("Aborted", "AbortError"));
              });
            }
          }) as unknown as Promise<Response>,
      );

      const files = [new File(["content"], "test.txt", { type: "text/plain" })];
      const controller = new AbortController();
      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();

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
      const files = [new File(["content"], "test.txt", { type: "text/plain" })];
      const controller = new AbortController();
      controller.abort(); // Abort before calling the function

      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();

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
      fetchMock.mockRejectedValueOnce(new Error("Network error"));

      const files = [new File(["content"], "test.txt", { type: "text/plain" })];
      const controller = new AbortController();
      const consoleErrorSpy = jest.spyOn(console, "error").mockImplementation();

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
      fetchMock.mockResponseOnce(JSON.stringify(mockResponse));

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
