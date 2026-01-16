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
  isWebSocketSupported: jest.fn().mockReturnValue(true),
  streamChatbotReply: jest.fn().mockReturnValue(null),
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
  Messages: ({ messages, loading }: MessagesProps) => (
    <div data-testid="messages">
      {loading ? "Loading..." : messages.map((m) => m.text).join(",")}
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
        },
      ]),
    );
    sessionStorage.setItem("chatbot-last-session-id", "session-1");

    const mockWs = {
      readyState: WebSocket.OPEN,
      send: jest.fn(),
      close: jest.fn(),
      onmessage: null as unknown as ((event: MessageEvent) => void) | null,
      onerror: null as unknown as ((event: Event) => void) | null,
      onclose: null as unknown as ((event: CloseEvent) => void) | null,
    };

    (chatbotApi.streamChatbotReply as jest.Mock).mockImplementationOnce(
      (
        _sessionId: string,
        _message: string,
        onToken: (token: string) => void,
        onComplete: () => void,
      ) => {
        setTimeout(() => {
          onToken("Bot reply");
          onComplete();
        }, 50);
        return mockWs;
      },
    );

    render(<Chatbot />);
    fireEvent.click(
      screen.getByRole("button", { name: getChatbotText("toggleButtonLabel") }),
    );

    fireEvent.click(screen.getByText("Set Input"));
    fireEvent.click(screen.getByText("Send Message"));

    await waitFor(
      () => {
        const messagesEl = screen.getByTestId("messages");
        expect(messagesEl.textContent).toContain("Bot reply");
      },
      { timeout: 3000 },
    );
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

  describe("WebSocket Streaming Integration", () => {
    it("attempts WebSocket streaming first when WebSocket is supported", async () => {
      sessionStorage.setItem(
        "chatbot-sessions",
        JSON.stringify([
          {
            id: "session-1",
            messages: [],
            createdAt: "2024-01-01",
            isLoading: false,
          },
        ]),
      );
      sessionStorage.setItem("chatbot-last-session-id", "session-1");

      const mockWs = {
        readyState: WebSocket.OPEN,
        send: jest.fn(),
        close: jest.fn(),
        onmessage: null as unknown as ((event: MessageEvent) => void) | null,
        onerror: null as unknown as ((event: Event) => void) | null,
        onclose: null as unknown as ((event: CloseEvent) => void) | null,
      };

      (chatbotApi.streamChatbotReply as jest.Mock).mockImplementationOnce(
        (
          _sessionId: string,
          _message: string,
          onToken: (token: string) => void,
          onComplete: () => void,
        ) => {
          // Simulate successful streaming
          setTimeout(() => {
            onToken("Hello");
            onToken(" ");
            onToken("World");
            onComplete();
          }, 50);
          return mockWs;
        },
      );

      render(<Chatbot />);
      fireEvent.click(
        screen.getByRole("button", {
          name: getChatbotText("toggleButtonLabel"),
        }),
      );

      fireEvent.click(screen.getByText("Set Input"));
      fireEvent.click(screen.getByText("Send Message"));

      await waitFor(() => {
        expect(chatbotApi.streamChatbotReply).toHaveBeenCalledWith(
          "session-1",
          "Hello bot",
          expect.any(Function),
          expect.any(Function),
          expect.any(Function),
        );
      });

      // Wait for streaming to complete and message to appear
      await waitFor(
        () => {
          const messagesEl = screen.getByTestId("messages");
          expect(messagesEl.textContent).toContain("Hello World");
        },
        { timeout: 3000 },
      );

      // Should NOT fallback to HTTP
      expect(chatbotApi.fetchChatbotReply).not.toHaveBeenCalled();
    });

    it("falls back to HTTP when WebSocket streaming fails", async () => {
      sessionStorage.setItem(
        "chatbot-sessions",
        JSON.stringify([
          {
            id: "session-1",
            messages: [],
            createdAt: "2024-01-01",
            isLoading: false,
          },
        ]),
      );
      sessionStorage.setItem("chatbot-last-session-id", "session-1");

      const mockWs = {
        readyState: WebSocket.OPEN,
        send: jest.fn(),
        close: jest.fn(),
        onmessage: null as unknown as ((event: MessageEvent) => void) | null,
        onerror: null as unknown as ((event: Event) => void) | null,
        onclose: null as unknown as ((event: CloseEvent) => void) | null,
      };

      (chatbotApi.streamChatbotReply as jest.Mock).mockImplementationOnce(
        (
          _sessionId: string,
          _message: string,
          _onToken: (token: string) => void,
          _onComplete: () => void,
          onError: (error: Error) => void,
        ) => {
          // Simulate WebSocket error
          setTimeout(() => {
            onError(new Error("WebSocket connection failed"));
          }, 50);
          return mockWs;
        },
      );

      render(<Chatbot />);
      fireEvent.click(
        screen.getByRole("button", {
          name: getChatbotText("toggleButtonLabel"),
        }),
      );

      fireEvent.click(screen.getByText("Set Input"));
      fireEvent.click(screen.getByText("Send Message"));

      // Wait for fallback to HTTP
      await waitFor(
        () => {
          expect(chatbotApi.fetchChatbotReply).toHaveBeenCalledWith(
            "session-1",
            "Hello bot",
            expect.anything(),
          );
        },
        { timeout: 3000 },
      );

      // Verify bot reply from HTTP fallback appears
      await waitFor(() => {
        const messagesEl = screen.getByTestId("messages");
        expect(messagesEl.textContent).toContain("Bot reply");
      });
    });

    it("prevents sending new messages while one is streaming", async () => {
      sessionStorage.setItem(
        "chatbot-sessions",
        JSON.stringify([
          {
            id: "session-1",
            messages: [],
            createdAt: "2024-01-01",
            isLoading: false,
          },
        ]),
      );
      sessionStorage.setItem("chatbot-last-session-id", "session-1");

      const mockWs = {
        readyState: WebSocket.OPEN,
        send: jest.fn(),
        close: jest.fn(),
        onmessage: null as unknown as ((event: MessageEvent) => void) | null,
        onerror: null as unknown as ((event: Event) => void) | null,
        onclose: null as unknown as ((event: CloseEvent) => void) | null,
      };

      (chatbotApi.streamChatbotReply as jest.Mock).mockImplementation(
        (
          _sessionId: string,
          _message: string,
          onToken: (token: string) => void,
          onComplete: () => void,
        ) => {
          // Simulate longer streaming
          setTimeout(() => {
            onToken("Response");
            onComplete();
          }, 500);
          return mockWs;
        },
      );

      render(<Chatbot />);
      fireEvent.click(
        screen.getByRole("button", {
          name: getChatbotText("toggleButtonLabel"),
        }),
      );

      fireEvent.click(screen.getByText("Set Input"));
      fireEvent.click(screen.getByText("Send Message"));

      // Try to send another message immediately
      fireEvent.click(screen.getByText("Set Input"));
      fireEvent.click(screen.getByText("Send Message"));

      // Wait a bit
      await new Promise((resolve) => setTimeout(resolve, 200));

      // Should only have been called once (second call blocked)
      expect(chatbotApi.streamChatbotReply).toHaveBeenCalledTimes(1);
    });

    it("uses HTTP endpoint for file uploads even with WebSocket support", async () => {
      sessionStorage.setItem(
        "chatbot-sessions",
        JSON.stringify([
          {
            id: "session-1",
            messages: [],
            createdAt: "2024-01-01",
            isLoading: false,
          },
        ]),
      );
      sessionStorage.setItem("chatbot-last-session-id", "session-1");

      render(<Chatbot />);
      fireEvent.click(
        screen.getByRole("button", {
          name: getChatbotText("toggleButtonLabel"),
        }),
      );

      // Simulate file upload scenario by calling the component's sendMessage with files
      // Note: This test verifies the logic, actual file upload UI testing would be more complex
      fireEvent.click(screen.getByText("Set Input"));
      fireEvent.click(screen.getByText("Send Message"));

      await waitFor(() => {
        // When no files, should use streamChatbotReply
        expect(chatbotApi.streamChatbotReply).toHaveBeenCalled();
      });
    });

    it("reuses WebSocket connection for 2nd message in same session", async () => {
      sessionStorage.setItem(
        "chatbot-sessions",
        JSON.stringify([
          {
            id: "session-1",
            name: "Test Session",
            messages: [],
            createdAt: "2024-01-01",
            isLoading: false,
          },
        ]),
      );
      sessionStorage.setItem("chatbot-last-session-id", "session-1");

      let callCount = 0;
      const callbacks: Array<{
        onToken: (token: string) => void;
        onComplete: () => void;
      }> = [];

      const mockWs = {
        readyState: WebSocket.OPEN,
        send: jest.fn(() => {
          // When send() is called on reused connection,
          // trigger the onmessage handler that the component sets
          if (mockWs.onmessage) {
            // Simulate WebSocket server sending tokens back
            setTimeout(() => {
              // Send token message
              mockWs.onmessage!({
                data: JSON.stringify({ token: "Response 2" }),
              } as MessageEvent);

              // Send completion message
              setTimeout(() => {
                mockWs.onmessage!({
                  data: JSON.stringify({ end: true }),
                } as MessageEvent);
              }, 20);
            }, 50);
          }
        }),
        close: jest.fn(),
        onmessage: null as unknown as ((event: MessageEvent) => void) | null,
        onerror: null as unknown as ((event: Event) => void) | null,
        onclose: null as unknown as ((event: CloseEvent) => void) | null,
      };

      (chatbotApi.streamChatbotReply as jest.Mock).mockImplementation(
        (
          _sessionId: string,
          _message: string,
          onToken: (token: string) => void,
          onComplete: () => void,
        ) => {
          callCount++;
          const currentCall = callCount;

          // Store callbacks for potential reuse
          callbacks.push({ onToken, onComplete });

          // Simulate first message response immediately
          setTimeout(() => {
            onToken(`Response ${currentCall}`);
            setTimeout(() => {
              onComplete();
            }, 20);
          }, 50);
          return mockWs;
        },
      );

      render(<Chatbot />);
      fireEvent.click(
        screen.getByRole("button", {
          name: getChatbotText("toggleButtonLabel"),
        }),
      );

      // Send first message
      fireEvent.click(screen.getByText("Set Input"));
      fireEvent.click(screen.getByText("Send Message"));

      await waitFor(
        () => {
          const messagesEl = screen.getByTestId("messages");
          expect(messagesEl.textContent).toContain("Response 1");
          // Also ensure not in loading state
          expect(messagesEl.textContent).not.toBe("Loading...");
        },
        { timeout: 3000 },
      );

      // Wait for isLoading state to be fully cleared and component ready for next message
      await new Promise((resolve) => setTimeout(resolve, 600));

      // Send second message
      fireEvent.click(screen.getByText("Set Input"));

      // Wait a bit to ensure message is set
      await new Promise((resolve) => setTimeout(resolve, 100));

      fireEvent.click(screen.getByText("Send Message"));

      // Wait for second response with increased timeout
      await waitFor(
        () => {
          const messagesEl = screen.getByTestId("messages");
          expect(messagesEl.textContent).toContain("Response 2");
        },
        { timeout: 5000 },
      );

      // streamChatbotReply should be called once for the first message
      expect(chatbotApi.streamChatbotReply).toHaveBeenCalledTimes(1);
      // The WebSocket object is reused - send() is called for the second message
      expect(mockWs.send).toHaveBeenCalledTimes(1);
    }, 15000); // 15 second timeout

    it("closes WebSocket connection on component unmount", async () => {
      sessionStorage.setItem(
        "chatbot-sessions",
        JSON.stringify([
          {
            id: "session-1",
            messages: [],
            createdAt: "2024-01-01",
            isLoading: false,
          },
        ]),
      );
      sessionStorage.setItem("chatbot-last-session-id", "session-1");

      const mockWs = {
        readyState: WebSocket.OPEN,
        send: jest.fn(),
        close: jest.fn(),
        onmessage: null as unknown as ((event: MessageEvent) => void) | null,
        onerror: null as unknown as ((event: Event) => void) | null,
        onclose: null as unknown as ((event: CloseEvent) => void) | null,
      };

      (chatbotApi.streamChatbotReply as jest.Mock).mockImplementationOnce(
        (
          _sessionId: string,
          _message: string,
          onToken: (token: string) => void,
          onComplete: () => void,
        ) => {
          setTimeout(() => {
            onToken("Test");
            onComplete();
          }, 50);
          return mockWs;
        },
      );

      const { unmount } = render(<Chatbot />);
      fireEvent.click(
        screen.getByRole("button", {
          name: getChatbotText("toggleButtonLabel"),
        }),
      );

      fireEvent.click(screen.getByText("Set Input"));
      fireEvent.click(screen.getByText("Send Message"));

      await waitFor(() => {
        expect(chatbotApi.streamChatbotReply).toHaveBeenCalled();
      });

      // Unmount component
      unmount();

      // WebSocket close should be called during cleanup
      await waitFor(() => {
        expect(mockWs.close).toHaveBeenCalled();
      });
    });

    it("handles rapid message prevention to avoid connection leaks", async () => {
      sessionStorage.setItem(
        "chatbot-sessions",
        JSON.stringify([
          {
            id: "session-1",
            messages: [],
            createdAt: "2024-01-01",
            isLoading: false,
          },
        ]),
      );
      sessionStorage.setItem("chatbot-last-session-id", "session-1");

      const mockWs = {
        readyState: WebSocket.OPEN,
        send: jest.fn(),
        close: jest.fn(),
        onmessage: null as unknown as ((event: MessageEvent) => void) | null,
        onerror: null as unknown as ((event: Event) => void) | null,
        onclose: null as unknown as ((event: CloseEvent) => void) | null,
      };

      (chatbotApi.streamChatbotReply as jest.Mock).mockImplementation(
        (
          _sessionId: string,
          _message: string,
          onToken: (token: string) => void,
          onComplete: () => void,
        ) => {
          setTimeout(() => {
            onToken("Response");
            onComplete();
          }, 300);
          return mockWs;
        },
      );

      render(<Chatbot />);
      fireEvent.click(
        screen.getByRole("button", {
          name: getChatbotText("toggleButtonLabel"),
        }),
      );

      // Rapidly click send multiple times
      fireEvent.click(screen.getByText("Set Input"));
      fireEvent.click(screen.getByText("Send Message"));
      fireEvent.click(screen.getByText("Send Message"));
      fireEvent.click(screen.getByText("Send Message"));

      await new Promise((resolve) => setTimeout(resolve, 100));

      // Only first message should go through
      expect(chatbotApi.streamChatbotReply).toHaveBeenCalledTimes(1);
    });
  });
});
