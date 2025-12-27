import { render, screen, fireEvent } from "@testing-library/react";
import { Input } from "../components/Input";

describe("Input Component", () => {
  const mockSetInput = jest.fn();
  const mockOnSend = jest.fn();

  beforeEach(() => {
    mockSetInput.mockReset();
    mockOnSend.mockReset();
  });

  it("renders textarea and send button", () => {
    render(
      <Input
        input=""
        setInput={mockSetInput}
        onSend={mockOnSend}
        onCancel={function (): void {
          throw new Error("Function not implemented.");
        }}
        loading={false}
      />,
    );
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("calls setInput when typing", () => {
    render(
      <Input
        input=""
        setInput={mockSetInput}
        onSend={mockOnSend}
        onCancel={function (): void {
          throw new Error("Function not implemented.");
        }}
        loading={false}
      />,
    );
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "Hello" },
    });
    expect(mockSetInput).toHaveBeenCalledWith("Hello");
  });

  it("calls onSend when Enter is pressed", () => {
    render(
      <Input
        input="Some text"
        setInput={mockSetInput}
        onSend={mockOnSend}
        onCancel={function (): void {
          throw new Error("Function not implemented.");
        }}
        loading={false}
      />,
    );
    fireEvent.keyDown(screen.getByRole("textbox"), {
      key: "Enter",
      shiftKey: false,
    });
    expect(mockOnSend).toHaveBeenCalled();
  });

  it("does not call onSend when Shift+Enter is pressed", () => {
    render(
      <Input
        input="Some text"
        setInput={mockSetInput}
        onSend={mockOnSend}
        onCancel={function (): void {
          throw new Error("Function not implemented.");
        }}
        loading={false}
      />,
    );
    fireEvent.keyDown(screen.getByRole("textbox"), {
      key: "Enter",
      shiftKey: true,
    });
    expect(mockOnSend).not.toHaveBeenCalled();
  });

  it("disables the send button when input is empty or whitespace", () => {
    const { rerender } = render(
      <Input
        input=""
        setInput={mockSetInput}
        onSend={mockOnSend}
        onCancel={function (): void {
          throw new Error("Function not implemented.");
        }}
        loading={false}
      />,
    );
    expect(screen.getByRole("button")).toBeDisabled();

    rerender(
      <Input
        input="    "
        setInput={mockSetInput}
        onSend={mockOnSend}
        onCancel={function (): void {
          throw new Error("Function not implemented.");
        }}
        loading={false}
      />,
    );
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("enables the send button when input has text", () => {
    render(
      <Input
        input="Hello"
        setInput={mockSetInput}
        onSend={mockOnSend}
        onCancel={function (): void {
          throw new Error("Function not implemented.");
        }}
        loading={false}
      />,
    );
    expect(screen.getByRole("button")).toBeEnabled();
  });

  it("calls onSend when button is clicked", () => {
    render(
      <Input
        input="Test message"
        setInput={mockSetInput}
        onSend={mockOnSend}
        onCancel={function (): void {
          throw new Error("Function not implemented.");
        }}
        loading={false}
      />,
    );
    fireEvent.click(screen.getByRole("button"));
    expect(mockOnSend).toHaveBeenCalled();
  });
});
