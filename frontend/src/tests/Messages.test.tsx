import { render, screen } from "@testing-library/react";
import { Messages } from "../components/Messages";
import { type Message } from "../model/Message";
import { getChatbotText } from "../data/chatbotTexts";

jest.mock("../data/chatbotTexts", () => ({
  getChatbotText: (key: string) => {
    if (key === "generatingMessage") return "Generating reply...";
    return key;
  },
}));

describe("Messages component", () => {
  const exampleMessages: Message[] = [
    { id: "1", sender: "user", text: "Hello" },
    { id: "2", sender: "jenkins-bot", text: "Hi there!" },
  ];

  beforeAll(() => {
    window.HTMLElement.prototype.scrollIntoView = jest.fn();
  });

  it("renders a single message", () => {
    render(
      <Messages
        messages={[exampleMessages[0]]}
        isLoading={false}
        loadingStatus={null}
      />,
    );
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("renders multiple messages", () => {
    render(
      <Messages
        messages={exampleMessages}
        isLoading={false}
        loadingStatus={null}
      />,
    );
    expect(screen.getByText("Hello")).toBeInTheDocument();
    expect(screen.getByText("Hi there!")).toBeInTheDocument();
  });

  it("splits multiline message into separate lines", () => {
    const multiLineMessage: Message = {
      id: "3",
      sender: "user",
      text: "Line 1\nLine 2\nLine 3",
    };

    render(
      <Messages
        messages={[multiLineMessage]}
        isLoading={false}
        loadingStatus={null}
      />,
    );

    expect(
      screen.getByText((content) => content.includes("Line 1")),
    ).toBeInTheDocument();
    expect(
      screen.getByText((content) => content.includes("Line 2")),
    ).toBeInTheDocument();
    expect(
      screen.getByText((content) => content.includes("Line 3")),
    ).toBeInTheDocument();
  });

  it("renders loading message when loading is true", () => {
    render(
      <Messages
        messages={[]}
        isLoading={true}
        loadingStatus={getChatbotText("generatingMessage")}
      />,
    );
    expect(
      screen.getByText(getChatbotText("generatingMessage")),
    ).toBeInTheDocument();
  });

  it("calls scrollIntoView when messages change", () => {
    const { rerender } = render(
      <Messages messages={[]} isLoading={false} loadingStatus={null} />,
    );

    const scrollMock = window.HTMLElement.prototype.scrollIntoView as jest.Mock;
    scrollMock.mockClear();

    rerender(
      <Messages
        messages={[{ id: "1", sender: "user", text: "Hello" }]}
        isLoading={false}
        loadingStatus={null}
      />,
    );

    expect(scrollMock).toHaveBeenCalledWith({ behavior: "smooth" });
  });
});
