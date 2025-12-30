import { render, screen, fireEvent } from "@testing-library/react";
import { getChatbotText } from "../data/chatbotTexts";
import { Header } from "../components/Header";
import type { Message } from "../model/Message";

const mockMessages: Message[] = [];

describe("Header Component", () => {
  const mockOpenSideBar = jest.fn();
  const mockClearMessages = jest.fn();

  beforeEach(() => {
    mockOpenSideBar.mockReset();
    mockClearMessages.mockReset();
  });

  it("always renders the sidebar toggle button", () => {
    render(
      <Header
        currentSessionId={null}
        openSideBar={mockOpenSideBar}
        clearMessages={mockClearMessages}
        messages={mockMessages}
      />
    );

    const sidebarButton = screen.getByRole("button", {
      name: "Toggle sidebar",
    });
    expect(sidebarButton).toBeInTheDocument();
  });

  it("does not render clear button when currentSessionId is null", () => {
    render(
      <Header
        currentSessionId={null}
        openSideBar={mockOpenSideBar}
        clearMessages={mockClearMessages}
        messages={mockMessages}
      />
    );

    const clearButton = screen.queryByRole("button", {
      name: getChatbotText("clearChat"),
    });
    expect(clearButton).not.toBeInTheDocument();
  });

  it("renders clear button when currentSessionId is not null", () => {
    render(
      <Header
        currentSessionId="session-1"
        openSideBar={mockOpenSideBar}
        clearMessages={mockClearMessages}
        messages={mockMessages}
      />
    );

    const clearButton = screen.getByRole("button", {
      name: getChatbotText("clearChat"),
    });
    expect(clearButton).toBeInTheDocument();
  });

  it("calls openSideBar when sidebar button is clicked", () => {
    render(
      <Header
        currentSessionId={null}
        openSideBar={mockOpenSideBar}
        clearMessages={mockClearMessages}
        messages={mockMessages}
      />
    );

    const sidebarButton = screen.getByRole("button", {
      name: "Toggle sidebar",
    });
    fireEvent.click(sidebarButton);

    expect(mockOpenSideBar).toHaveBeenCalled();
  });

  it("calls clearMessages with session ID when clear button is clicked", () => {
    render(
      <Header
        currentSessionId="session-1"
        openSideBar={mockOpenSideBar}
        clearMessages={mockClearMessages}
        messages={mockMessages}
      />
    );

    const clearButton = screen.getByRole("button", {
      name: getChatbotText("clearChat"),
    });
    fireEvent.click(clearButton);

    expect(mockClearMessages).toHaveBeenCalledWith("session-1");
  });
});
