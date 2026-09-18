import { render, screen, fireEvent } from "@testing-library/react";
import { getChatbotText } from "../data/chatbotTexts";
import { Header } from "../components/Header";
import type { Message } from "../model/Message";
import type { ProviderMetadata } from "../api/chatbot";

const mockMessages: Message[] = [];
const mockProviders: ProviderMetadata[] = [
  {
    id: "local",
    label: "Local Mistral Model",
    model: "llama.cpp",
    configured: true,
  },
  {
    id: "groq",
    label: "Groq API",
    model: "groq/llama-3.1-8b-instant",
    configured: true,
  },
  {
    id: "gemini",
    label: "Gemini API",
    model: "gemini/gemini-3.5-flash-lite",
    configured: false,
  },
];

describe("Header Component", () => {
  const mockOpenSideBar = jest.fn();
  const mockClearMessages = jest.fn();
  const mockProviderChange = jest.fn();

  beforeEach(() => {
    mockOpenSideBar.mockReset();
    mockClearMessages.mockReset();
    mockProviderChange.mockReset();
  });

  it("always renders the sidebar toggle button", () => {
    render(
      <Header
        currentSessionId={null}
        openSideBar={mockOpenSideBar}
        clearMessages={mockClearMessages}
        messages={mockMessages}
      />,
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
      />,
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
      />,
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
      />,
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
      />,
    );

    const clearButton = screen.getByRole("button", {
      name: getChatbotText("clearChat"),
    });
    fireEvent.click(clearButton);

    expect(mockClearMessages).toHaveBeenCalledWith("session-1");
  });

  it("selects a configured provider", () => {
    render(
      <Header
        currentSessionId={null}
        openSideBar={mockOpenSideBar}
        clearMessages={mockClearMessages}
        messages={mockMessages}
        providers={mockProviders}
        selectedProviderId="local"
        onProviderChange={mockProviderChange}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Select model provider" }),
    );
    fireEvent.click(screen.getByRole("option", { name: "Groq API" }));

    expect(mockProviderChange).toHaveBeenCalledWith("groq");
  });

  it("does not select an unconfigured provider", () => {
    render(
      <Header
        currentSessionId={null}
        openSideBar={mockOpenSideBar}
        clearMessages={mockClearMessages}
        messages={mockMessages}
        providers={mockProviders}
        selectedProviderId="local"
        onProviderChange={mockProviderChange}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Select model provider" }),
    );

    fireEvent.click(
      screen.getByRole("option", {
        name: "Gemini API, API key not configured",
      }),
    );
    expect(mockProviderChange).not.toHaveBeenCalled();
  });
});
