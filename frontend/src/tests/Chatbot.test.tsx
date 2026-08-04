import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Chatbot } from "../components/Chatbot";
import * as chatbotApi from "../api/chatbot";
import { getChatbotText } from "../data/chatbotTexts";
import type { HeaderProps } from "../components/Header";
import type { InputProps } from "../components/Input";
import type { MessagesProps } from "../components/Messages";

jest.mock("../api/chatbot", () => ({
  fetchChatbotReply: jest.fn().mockResolvedValue({
    id: "bot-msg-1",
    sender: "jenkins-bot",
    text: "Bot reply",
  }),
  fetchChatbotReplyWithFiles: jest.fn().mockResolvedValue({
    id: "bot-msg-1",
    sender: "jenkins-bot",
    text: "Bot reply with files",
  }),
  createChatSession: jest.fn().mockResolvedValue("new-session-id"),
  deleteChatSession: jest.fn().mockResolvedValue(undefined),
  fetchSupportedExtensions: jest.fn().mockResolvedValue(null),
  validateFile: jest.fn().mockReturnValue({ isValid: true }),
  fileToAttachment: jest.fn().mockReturnValue({
    filename: "test.txt",
    type: "text",
    size: 100,
    mimeType: "text/plain",
  }),
}));

jest.mock("uuid", () => ({
  v4: () => "user-msg-id",
}));

jest.mock("../components/Header", () => ({
  Header: ({ clearMessages, onClose }: HeaderProps) => (
    <div data-testid="header">
      <button onClick={() => clearMessages("session-1")}>Clear Chat</button>
      <button onClick={onClose}>Close Widget</button>
    </div>
  ),
}));

jest.mock("../components/Input", () => ({
  Input: ({ setInput, onSend, onCancel, isLoading }: InputProps) => (
    <div data-testid="input">
      <button onClick={() => setInput("Hello bot")}>Set Input</button>
      <button onClick={onSend}>Send Message</button>
      {isLoading && <button onClick={onCancel}>Cancel Message</button>}
    </div>
  ),
}));

jest.mock("../components/Messages", () => ({
  Messages: ({ messages, loadingStatus }: MessagesProps) => (
    <div data-testid="messages">
      {loadingStatus ? "Loading..." : messages.map((m) => m.text).join(",")}
    </div>
  ),
}));

describe("Chatbot component", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorage.clear();
  });

  it("shows welcome page when no sessions exist on mount", () => {
    render(<Chatbot />);
    expect(
      screen.getByText(getChatbotText("welcomeMessage"))
    ).toBeInTheDocument();
  });

  it("creates a new chat when clicking start chat button", async () => {
    render(<Chatbot />);
    fireEvent.click(
      screen.getByRole("button", { name: getChatbotText("createNewChat") })
    );

    await waitFor(() =>
      expect(screen.getByTestId("messages")).toBeInTheDocument()
    );
  });

  it("sends a message and shows bot reply", async () => {
    sessionStorage.setItem(
      "chatbot-sessions",
      JSON.stringify([
        {
          id: "session-1",
          messages: [],
          createdAt: "2024-01-01",
          isLoading: false,
          loadingStatus: null,
        },
      ])
    );
    sessionStorage.setItem("chatbot-last-session-id", "session-1");

    render(<Chatbot />);
    expect(screen.getByTestId("messages")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Set Input"));
    fireEvent.click(screen.getByText("Send Message"));

    await waitFor(() => {
      expect(chatbotApi.fetchChatbotReply).toHaveBeenCalledWith(
        "session-1",
        "Hello bot",
        expect.anything()
      );
    });
  });

  it("calls onClose when close widget button is clicked", () => {
    const mockOnClose = jest.fn();
    render(<Chatbot onClose={mockOnClose} />);

    fireEvent.click(screen.getByText("Close Widget"));
    expect(mockOnClose).toHaveBeenCalled();
  });

  it("opens delete popup and can cancel or delete", async () => {
    sessionStorage.setItem(
      "chatbot-sessions",
      JSON.stringify([
        {
          id: "session-1",
          messages: [],
          createdAt: "2024-01-01",
          isLoading: false,
          loadingStatus: null,
        },
      ])
    );
    sessionStorage.setItem("chatbot-last-session-id", "session-1");

    render(<Chatbot />);
    fireEvent.click(screen.getByText("Clear Chat"));

    expect(screen.getByText(getChatbotText("popupTitle"))).toBeInTheDocument();

    // Cancel
    fireEvent.click(screen.getByText(getChatbotText("popupCancelButton")));
    expect(
      screen.queryByText(getChatbotText("popupTitle"))
    ).not.toBeInTheDocument();

    // Re-open and delete
    fireEvent.click(screen.getByText("Clear Chat"));
    fireEvent.click(screen.getByText(getChatbotText("popupDeleteButton")));

    await waitFor(() =>
      expect(chatbotApi.deleteChatSession).toHaveBeenCalledWith("session-1")
    );
  });
});
