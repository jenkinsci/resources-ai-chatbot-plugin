import { render, screen, fireEvent } from "@testing-library/react";
import { Sidebar } from "../components/Sidebar";
import type { ChatSession } from "../model/ChatSession";
import { getChatbotText } from "../data/chatbotTexts";

jest.mock("../data/chatbotTexts", () => ({
  getChatbotText: (key: string) => key,
}));

const baseProps = {
  onClose: jest.fn(),
  onCreateChat: jest.fn(),
  onSwitchChat: jest.fn(),
  openConfirmDeleteChatPopup: jest.fn(),
  activeChatId: null as string | null,
};

const exampleChats: ChatSession[] = [
  {
    id: "chat-1",
    messages: [],
    createdAt: "2024-01-01T00:00:00Z",
    isLoading: false,
    loadingStatus: null,
  },
  {
    id: "chat-2",
    messages: [{ id: "msg-1", sender: "user", text: "Hello world" }],
    createdAt: "2024-01-02T00:00:00Z",
    isLoading: false,
    loadingStatus: null,
  },
];

describe("Sidebar component", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders close and new chat buttons", () => {
    render(<Sidebar {...baseProps} chatList={[]} />);
    expect(
      screen.getByText(getChatbotText("sidebarCreateNewChat")),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Close Sidebar" }),
    ).toBeInTheDocument();
  });

  it("renders no chats message when chatList is empty", () => {
    render(<Sidebar {...baseProps} chatList={[]} />);
    expect(
      screen.getByText(getChatbotText("sidebarNoActiveChats")),
    ).toBeInTheDocument();
  });

  it("renders chat list with correct chat names", () => {
    render(<Sidebar {...baseProps} chatList={exampleChats} />);
    expect(screen.getByText("Chat 1")).toBeInTheDocument();
    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    render(<Sidebar {...baseProps} chatList={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "Close Sidebar" }));
    expect(baseProps.onClose).toHaveBeenCalled();
  });

  it("calls onClose and onCreateChat when new chat button is clicked", () => {
    render(<Sidebar {...baseProps} chatList={[]} />);
    fireEvent.click(screen.getByText(getChatbotText("sidebarCreateNewChat")));
    expect(baseProps.onClose).toHaveBeenCalled();
    expect(baseProps.onCreateChat).toHaveBeenCalled();
  });

  it("calls onSwitchChat when a chat row is clicked", () => {
    render(<Sidebar {...baseProps} chatList={exampleChats} />);
    fireEvent.click(screen.getByText("Chat 1"));
    expect(baseProps.onSwitchChat).toHaveBeenCalledWith("chat-1");
  });

  it("calls openConfirmDeleteChatPopup when delete button is clicked", () => {
    render(<Sidebar {...baseProps} chatList={exampleChats} />);
    const deleteButton = screen.getAllByRole("button", {
      name: "Delete Chat",
    })[0];
    fireEvent.click(deleteButton);
    expect(baseProps.openConfirmDeleteChatPopup).toHaveBeenCalledWith("chat-1");
  });

  it("renders active chat styling when activeChatId matches", () => {
    render(
      <Sidebar {...baseProps} chatList={exampleChats} activeChatId="chat-2" />,
    );
    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });

  it("renders full chat name when first message text is 25 characters or less", () => {
    const shortMessageChat: ChatSession = {
      id: "chat-short",
      messages: [{ id: "msg-1", sender: "user", text: "Short message" }],
      createdAt: "2024-01-01T00:00:00Z",
      isLoading: false,
      loadingStatus: null,
    };

    render(<Sidebar {...baseProps} chatList={[shortMessageChat]} />);
    expect(screen.getByText("Short message")).toBeInTheDocument();
  });

  it("truncates chat name when first message text exceeds 25 characters", () => {
    const longMessageChat: ChatSession = {
      id: "chat-long",
      messages: [
        {
          id: "msg-1",
          sender: "user",
          text: "This is a very long message that should be truncated properly.",
        },
      ],
      createdAt: "2024-01-03T00:00:00Z",
      isLoading: false,
      loadingStatus: null,
    };

    render(
      <Sidebar
        {...baseProps}
        chatList={[longMessageChat]}
        activeChatId={null}
      />,
    );

    const expectedTruncated = "This is a very long messa...";

    expect(screen.getByText(expectedTruncated)).toBeInTheDocument();
  });
});
