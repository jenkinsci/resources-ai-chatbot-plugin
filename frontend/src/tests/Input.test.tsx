import { render, screen, fireEvent } from "@testing-library/react";
import { Input } from "../components/Input";

describe("Input Component", () => {
  const mockSetInput = jest.fn();
  const mockOnSend = jest.fn();
  const mockOnFilesAttached = jest.fn();
  const mockOnFileRemoved = jest.fn();
  const mockValidateFile = jest.fn().mockReturnValue({ isValid: true });

  beforeEach(() => {
    mockSetInput.mockReset();
    mockOnSend.mockReset();
    mockOnFilesAttached.mockReset();
    mockOnFileRemoved.mockReset();
    mockValidateFile.mockReset();
    mockValidateFile.mockReturnValue({ isValid: true });
  });

  it("renders textarea and send button", () => {
    render(<Input input="" setInput={mockSetInput} onSend={mockOnSend} />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
  });

  it("calls setInput when typing", () => {
    render(<Input input="" setInput={mockSetInput} onSend={mockOnSend} />);
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "Hello" },
    });
    expect(mockSetInput).toHaveBeenCalledWith("Hello");
  });

  it("calls onSend when Enter is pressed", () => {
    render(
      <Input input="Some text" setInput={mockSetInput} onSend={mockOnSend} />,
    );
    fireEvent.keyDown(screen.getByRole("textbox"), {
      key: "Enter",
      shiftKey: false,
    });
    expect(mockOnSend).toHaveBeenCalled();
  });

  it("does not call onSend when Shift+Enter is pressed", () => {
    render(
      <Input input="Some text" setInput={mockSetInput} onSend={mockOnSend} />,
    );
    fireEvent.keyDown(screen.getByRole("textbox"), {
      key: "Enter",
      shiftKey: true,
    });
    expect(mockOnSend).not.toHaveBeenCalled();
  });

  it("disables the send button when input is empty or whitespace", () => {
    const { rerender } = render(
      <Input input="" setInput={mockSetInput} onSend={mockOnSend} />,
    );
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();

    rerender(
      <Input input="    " setInput={mockSetInput} onSend={mockOnSend} />,
    );
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("enables the send button when input has text", () => {
    render(<Input input="Hello" setInput={mockSetInput} onSend={mockOnSend} />);
    expect(screen.getByRole("button", { name: /send/i })).toBeEnabled();
  });

  it("calls onSend when button is clicked", () => {
    render(
      <Input
        input="Test message"
        setInput={mockSetInput}
        onSend={mockOnSend}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /send/i }));
    expect(mockOnSend).toHaveBeenCalled();
  });

  describe("File Upload Features", () => {
    it("renders attach button when file upload is enabled", () => {
      render(
        <Input
          input=""
          setInput={mockSetInput}
          onSend={mockOnSend}
          enableFileUpload={true}
          onFilesAttached={mockOnFilesAttached}
        />,
      );
      expect(screen.getByTitle("Attach files")).toBeInTheDocument();
    });

    it("does not render attach button when file upload is disabled", () => {
      render(
        <Input
          input=""
          setInput={mockSetInput}
          onSend={mockOnSend}
          enableFileUpload={false}
        />,
      );
      expect(screen.queryByTitle("Attach files")).not.toBeInTheDocument();
    });

    it("displays attached files", () => {
      const mockFile = new File(["content"], "test.txt", {
        type: "text/plain",
      });
      Object.defineProperty(mockFile, "size", { value: 1024 });

      render(
        <Input
          input=""
          setInput={mockSetInput}
          onSend={mockOnSend}
          attachedFiles={[mockFile]}
          onFilesAttached={mockOnFilesAttached}
          onFileRemoved={mockOnFileRemoved}
        />,
      );

      expect(screen.getByText(/test\.txt/)).toBeInTheDocument();
    });

    it("enables send button when files are attached even with empty input", () => {
      const mockFile = new File(["content"], "test.txt", {
        type: "text/plain",
      });

      render(
        <Input
          input=""
          setInput={mockSetInput}
          onSend={mockOnSend}
          attachedFiles={[mockFile]}
          onFilesAttached={mockOnFilesAttached}
        />,
      );

      expect(screen.getByRole("button", { name: /send/i })).toBeEnabled();
    });

    it("calls onFileRemoved when remove button is clicked", () => {
      const mockFile = new File(["content"], "test.txt", {
        type: "text/plain",
      });

      render(
        <Input
          input=""
          setInput={mockSetInput}
          onSend={mockOnSend}
          attachedFiles={[mockFile]}
          onFilesAttached={mockOnFilesAttached}
          onFileRemoved={mockOnFileRemoved}
        />,
      );

      const removeButton = screen.getByTitle("Remove file");
      fireEvent.click(removeButton);

      expect(mockOnFileRemoved).toHaveBeenCalledWith(0);
    });

    it("shows image icon for image files", () => {
      const mockFile = new File(["content"], "photo.png", {
        type: "image/png",
      });

      render(
        <Input
          input=""
          setInput={mockSetInput}
          onSend={mockOnSend}
          attachedFiles={[mockFile]}
          onFilesAttached={mockOnFilesAttached}
        />,
      );

      expect(screen.getByTestId("file-icon-image")).toBeInTheDocument();
    });

    it("shows document icon for text files", () => {
      const mockFile = new File(["content"], "doc.txt", { type: "text/plain" });

      render(
        <Input
          input=""
          setInput={mockSetInput}
          onSend={mockOnSend}
          attachedFiles={[mockFile]}
          onFilesAttached={mockOnFilesAttached}
        />,
      );

      expect(screen.getByTestId("file-icon-document")).toBeInTheDocument();
    });

    it("triggers onFilesAttached when file input changes", () => {
      render(
        <Input
          input=""
          setInput={mockSetInput}
          onSend={mockOnSend}
          enableFileUpload={true}
          onFilesAttached={mockOnFilesAttached}
          validateFile={mockValidateFile}
        />,
      );

      const fileInput = document.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;
      const mockFile = new File(["content"], "test.txt", {
        type: "text/plain",
      });

      fireEvent.change(fileInput, { target: { files: [mockFile] } });

      expect(mockOnFilesAttached).toHaveBeenCalled();
    });

    it("keeps send button disabled with whitespace-only input and no files", () => {
      render(
        <Input
          input="   "
          setInput={mockSetInput}
          onSend={mockOnSend}
          attachedFiles={[]}
          onFilesAttached={mockOnFilesAttached}
        />,
      );

      expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
    });
  });
});
