import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Chatbot } from "../components/Chatbot";
import * as chatbotApi from "../api/chatbot";
import { getChatbotText } from "../data/chatbotTexts";
import type { SidebarProps } from "../components/Sidebar";
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

jest.mock("../components/Sidebar", () => ({
  Sidebar: ({
    onClose,
    onCreateChat,
    onSwitchChat,
    openConfirmDeleteChatPopup,
  }: SidebarProps) => (
    <div data-testid="sidebar">
      <button onClick={onClose}>Close Sidebar</button>
      <button onClick={onCreateChat}>New Chat</button>
      <button onClick={() => onSwitchChat("session-1")}>Switch Chat</button>
      <button onClick={() => openConfirmDeleteChatPopup("session-1")}>
        Delete Chat
      </button>
    </div>
  ),
}));

jest.mock("../components/Header", () => ({
  Header: ({ openSideBar, clearMessages }: HeaderProps) => (
    <div data-testid="header">
      <button onClick={openSideBar}>Open Sidebar</button>
      <button onClick={() => clearMessages("session-1")}>Clear Chat</button>
    </div>
  ),
}));

jest.mock("../components/Input", () => ({
  Input: ({ setInput, onSend }: InputProps) => (
    <div data-testid="input">
      <button onClick={() => setInput("Hello bot")}>Set Input</button>
      <button onClick={onSend}>Send Message</button>
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

  it("renders toggle button", () => {
    render(<Chatbot />);
    expect(
      screen.getByRole("button", { name: getChatbotText("toggleButtonLabel") }),
    ).toBeInTheDocument();
  });

  it("shows welcome page when no sessions exist", () => {
    render(<Chatbot />);
    fireEvent.click(
      screen.getByRole("button", { name: getChatbotText("toggleButtonLabel") }),
    );
    expect(
      screen.getByText(getChatbotText("welcomeMessage")),
    ).toBeInTheDocument();
  });

  it("creates a new chat when clicking create button", async () => {
    render(<Chatbot />);
    fireEvent.click(
      screen.getByRole("button", { name: getChatbotText("toggleButtonLabel") }),
    );
    fireEvent.click(
      screen.getByRole("button", { name: getChatbotText("createNewChat") }),
    );

    await waitFor(() =>
      expect(screen.getByTestId("messages")).toBeInTheDocument(),
    );
  });

  it("opens sidebar and switches chat", async () => {
    render(<Chatbot />);
    fireEvent.click(
      screen.getByRole("button", { name: getChatbotText("toggleButtonLabel") }),
    );

    fireEvent.click(screen.getByText("Open Sidebar"));
    expect(screen.getByTestId("sidebar")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Switch Chat"));
    expect(screen.getByTestId("messages")).toBeInTheDocument();
  });

  it("creates new chat from sidebar", async () => {
    render(<Chatbot />);
    fireEvent.click(
      screen.getByRole("button", { name: getChatbotText("toggleButtonLabel") }),
    );
    fireEvent.click(screen.getByText("Open Sidebar"));
    fireEvent.click(screen.getByText("New Chat"));

    await waitFor(() =>
      expect(screen.getByTestId("messages")).toBeInTheDocument(),
    );
  });

  it("deletes a chat", async () => {
    render(<Chatbot />);
    fireEvent.click(
      screen.getByRole("button", { name: getChatbotText("toggleButtonLabel") }),
    );
    fireEvent.click(screen.getByText("Open Sidebar"));
    fireEvent.click(screen.getByText("Delete Chat"));

    expect(screen.getByText(getChatbotText("popupTitle"))).toBeInTheDocument();

    fireEvent.click(screen.getByText(getChatbotText("popupDeleteButton")));

    await waitFor(() =>
      expect(chatbotApi.deleteChatSession).toHaveBeenCalledWith("session-1"),
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
      ]),
    );
    sessionStorage.setItem("chatbot-last-session-id", "session-1");

    render(<Chatbot />);
    fireEvent.click(
      screen.getByRole("button", { name: getChatbotText("toggleButtonLabel") }),
    );

    fireEvent.click(screen.getByText("Set Input"));
    fireEvent.click(screen.getByText("Send Message"));

    await waitFor(() => {
      expect(chatbotApi.fetchChatbotReply).toHaveBeenCalledWith(
        "session-1",
        "Hello bot",
        expect.anything(),
      );
    });
  });

  it("persists sessions on unmount", () => {
    render(<Chatbot />);
    fireEvent.click(
      screen.getByRole("button", { name: getChatbotText("toggleButtonLabel") }),
    );

    window.dispatchEvent(new Event("beforeunload"));

    expect(sessionStorage.getItem("chatbot-sessions")).toBeDefined();
    expect(sessionStorage.getItem("chatbot-last-session-id")).toBeDefined();
  });

  it("logs error when createChatSession returns empty id", async () => {
    const errorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    (chatbotApi.createChatSession as jest.Mock).mockResolvedValueOnce("");

    render(<Chatbot />);
    fireEvent.click(
      screen.getByRole("button", { name: getChatbotText("toggleButtonLabel") }),
    );
    fireEvent.click(screen.getByText(getChatbotText("createNewChat")));

    await waitFor(() => {
      expect(errorSpy).toHaveBeenCalledWith(
        "Add error showage for a couple of seconds.",
      );
    });

    errorSpy.mockRestore();
  });

  it("closes delete popup and resets sessionIdToDelete when cancel button is clicked", () => {
    render(<Chatbot />);
    fireEvent.click(
      screen.getByRole("button", { name: getChatbotText("toggleButtonLabel") }),
    );

    fireEvent.click(screen.getByText("Open Sidebar"));
    fireEvent.click(screen.getByText("Delete Chat"));

    expect(screen.getByText(getChatbotText("popupTitle"))).toBeInTheDocument();

    fireEvent.click(screen.getByText(getChatbotText("popupCancelButton")));
    expect(
      screen.queryByText(getChatbotText("popupTitle")),
    ).not.toBeInTheDocument();
  });

  it("closes the sidebar when onClose is called", () => {
    render(<Chatbot />);
    fireEvent.click(
      screen.getByRole("button", { name: getChatbotText("toggleButtonLabel") }),
    );

    fireEvent.click(screen.getByText("Open Sidebar"));
    expect(screen.getByTestId("sidebar")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Close Sidebar"));
    expect(screen.queryByTestId("sidebar")).not.toBeInTheDocument();
  });
});
