import { render, screen, fireEvent } from "@testing-library/react";
import { Header } from "../components/Header";
import type { Message } from "../model/Message";

const mockMessages: Message[] = [];

describe("Header Component", () => {
  const mockClearMessages = jest.fn();
  const mockSetIsDark = jest.fn();
  const mockOnClose = jest.fn();

  beforeEach(() => {
    mockClearMessages.mockReset();
    mockSetIsDark.mockReset();
    mockOnClose.mockReset();
  });

  it("always renders the close button and theme toggle", () => {
    render(
      <Header
        currentSessionId={null}
        clearMessages={mockClearMessages}
        messages={mockMessages}
        isDark={false}
        setIsDark={mockSetIsDark}
        onClose={mockOnClose}
      />
    );

    const closeButton = screen.getByRole("button", { name: "Close Chat" });
    const themeButton = screen.getByRole("button", { name: "Toggle Theme" });

    expect(closeButton).toBeInTheDocument();
    expect(themeButton).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    render(
      <Header
        currentSessionId={null}
        clearMessages={mockClearMessages}
        messages={mockMessages}
        isDark={false}
        setIsDark={mockSetIsDark}
        onClose={mockOnClose}
      />
    );

    const closeButton = screen.getByRole("button", { name: "Close Chat" });
    fireEvent.click(closeButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it("calls setIsDark when theme toggle is clicked", () => {
    render(
      <Header
        currentSessionId={null}
        clearMessages={mockClearMessages}
        messages={mockMessages}
        isDark={false}
        setIsDark={mockSetIsDark}
        onClose={mockOnClose}
      />
    );

    const themeButton = screen.getByRole("button", { name: "Toggle Theme" });
    fireEvent.click(themeButton);

    expect(mockSetIsDark).toHaveBeenCalledWith(true);
  });

  it("does not render clear or export button when currentSessionId is null", () => {
    render(
      <Header
        currentSessionId={null}
        clearMessages={mockClearMessages}
        messages={mockMessages}
        isDark={false}
        setIsDark={mockSetIsDark}
        onClose={mockOnClose}
      />
    );

    const deleteButton = screen.queryByRole("button", {
      name: "Delete chat session",
    });
    const exportButton = screen.queryByRole("button", {
      name: "Export chat history",
    });

    expect(deleteButton).not.toBeInTheDocument();
    expect(exportButton).not.toBeInTheDocument();
  });

  it("renders delete and export buttons when currentSessionId is not null", () => {
    render(
      <Header
        currentSessionId="session-1"
        clearMessages={mockClearMessages}
        messages={mockMessages}
        isDark={false}
        setIsDark={mockSetIsDark}
        onClose={mockOnClose}
      />
    );

    const deleteButton = screen.getByRole("button", {
      name: "Delete chat session",
    });
    const exportButton = screen.getByRole("button", {
      name: "Export chat history",
    });

    expect(deleteButton).toBeInTheDocument();
    expect(exportButton).toBeInTheDocument();
  });

  it("calls clearMessages with session ID when delete button is clicked", () => {
    render(
      <Header
        currentSessionId="session-1"
        clearMessages={mockClearMessages}
        messages={mockMessages}
        isDark={false}
        setIsDark={mockSetIsDark}
        onClose={mockOnClose}
      />
    );

    const deleteButton = screen.getByRole("button", {
      name: "Delete chat session",
    });
    fireEvent.click(deleteButton);

    expect(mockClearMessages).toHaveBeenCalledWith("session-1");
  });
});
