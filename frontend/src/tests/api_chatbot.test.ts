
import {
  createBotMessage,
  createChatSession,
  fetchChatbotReply,
  deleteChatSession
} from "../api/chatbot";
import { callChatbotApi } from "../utils/callChatbotApi";

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
 
  let consoleErrorSpy: jest.SpyInstance;

  beforeAll(() => {
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => { });
  });

  afterAll(() => {
    consoleErrorSpy.mockRestore();
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

      expect(callChatbotApi).toHaveBeenLastCalledWith(
        "sessions",
        { method: "POST" },
        { session_id: "" },
        expect.any(Number)
      );
    });

    it("returns empty result if session_id is missing in response", async () => {
      (callChatbotApi as jest.Mock).mockResolvedValueOnce({});

      const result = await createChatSession();

      expect(result).toBe("");
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to create chat session: session_id missing in response",
        {}
      );
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

      expect(callChatbotApi).toHaveBeenLastCalledWith(
        "sessions/session-xyz/message",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: "Hi!" }),
        },
        {},
        expect.any(Number),
        undefined,
      );
    });

    it("uses fallback error message when API reply is missing", async () => {
      (callChatbotApi as jest.Mock).mockResolvedValueOnce({});

      const result = await fetchChatbotReply("session-xyz", "Hi!");

      expect(result).toEqual({
        id: "mock-uuid",
        sender: "jenkins-bot",
        text: "Fallback error message",
      });
    });
  });
  describe("deleteChatSession", () => {
  it("calls API to delete chat session", async () => {
    (callChatbotApi as jest.Mock).mockResolvedValueOnce(undefined);

    await deleteChatSession("session-123");

    expect(callChatbotApi).toHaveBeenCalledWith(
      "sessions/session-123",
      { method: "DELETE" },
      undefined,
      expect.any(Number),
    );
  });
});

});

