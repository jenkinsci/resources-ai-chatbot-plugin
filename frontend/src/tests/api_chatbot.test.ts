import {
  createBotMessage,
  createChatSession,
  fetchChatbotReply,
  deleteChatSession,
} from "../api/chatbot";

import { callChatbotApi } from "../utils/callChatbotApi";
import { getChatbotText } from "../data/chatbotTexts";

jest.mock("uuid", () => ({
  v4: () => "mock-uuid",
}));

jest.mock("../utils/callChatbotApi", () => ({
  callChatbotApi: jest.fn(),
}));

jest.mock("../data/chatbotTexts", () => ({
  getChatbotText: jest.fn().mockReturnValue("Fallback error message"),
}));

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
});
