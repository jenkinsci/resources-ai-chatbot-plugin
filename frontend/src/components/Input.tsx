import { useRef } from "react";
import { getChatbotText } from "../data/chatbotTexts";
import { chatbotStyles } from "../styles/styles";

/**
 * Props for the Input component.
 */
export interface InputProps {
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  /** Optional: files attached to the message */
  attachedFiles?: File[];
  /** Optional: callback when files are attached */
  onFilesAttached?: (files: File[]) => void;
  /** Optional: callback when a file is removed */
  onFileRemoved?: (index: number) => void;
  /** Optional: whether file upload is enabled */
  enableFileUpload?: boolean;
  /** Optional: file validation function */
  validateFile?: (file: File) => { isValid: boolean; error?: string };
  /** Optional: whether a message is currently being sent */
  isLoading?: boolean;
  /** Optional: cancel the in-flight message */
  onCancel?: () => void;
}

/**
 * Input is a controlled textarea component for user message entry.
 * It supports multiline input and handles sending messages with Enter,
 * while allowing new lines with Shift+Enter. Optionally supports file uploads.
 */
export const Input = ({
  input,
  setInput,
  onSend,
  attachedFiles = [],
  onFilesAttached,
  onFileRemoved,
  enableFileUpload = true,
  validateFile,
  isLoading = false,
  onCancel,
}: InputProps) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !onFilesAttached) return;

    const validFiles: File[] = [];
    const errors: string[] = [];

    Array.from(files).forEach((file: File) => {
      const isDuplicate = attachedFiles.some(
        (existing) =>
          existing.name === file.name && existing.size === file.size,
      );

      if (isDuplicate) {
        return;
      }
      if (validateFile) {
        const validation = validateFile(file);
        if (validation.isValid) {
          validFiles.push(file);
        } else {
          errors.push(`${file.name}: ${validation.error}`);
        }
      } else {
        validFiles.push(file);
      }
    });

    if (errors.length > 0) {
      alert(`Some files could not be added:\n${errors.join("\n")}`);
    }

    if (validFiles.length > 0) {
      onFilesAttached([...attachedFiles, ...validFiles]);
    }

    // Reset the input so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleAttachClick = () => {
    fileInputRef.current?.click();
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const canSend = input.trim() || attachedFiles.length > 0;

  return (
    <div style={chatbotStyles.inputWrapper}>
      {/* Attached files preview */}
      {attachedFiles.length > 0 && (
        <div style={chatbotStyles.attachedFilesContainer}>
          {attachedFiles.map((file, index) => (
            <div
              key={`${file.name}-${index}`}
              style={chatbotStyles.attachedFileChip}
            >
              <span style={chatbotStyles.attachedFileName}>
                {file.type.startsWith("image/") ? (
                  <span data-testid="file-icon-image">🖼️</span>
                ) : (
                  <span data-testid="file-icon-document">📄</span>
                )}{" "}
                {file.name}
              </span>
              <span style={chatbotStyles.attachedFileSize}>
                ({formatFileSize(file.size)})
              </span>
              {onFileRemoved && (
                <button
                  onClick={() => onFileRemoved(index)}
                  style={chatbotStyles.removeFileButton}
                  title="Remove file"
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <div style={chatbotStyles.inputContainer}>
        {/* Hidden file input */}
        {enableFileUpload && (
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            style={{ display: "none" }}
            accept=".txt,.log,.md,.json,.xml,.yaml,.yml,.py,.js,.ts,.tsx,.java,.groovy,.sh,.png,.jpg,.jpeg,.gif,.webp,.bmp"
            aria-label="Upload files"
          />
        )}

        {/* Attach button */}
        {enableFileUpload && onFilesAttached && (
          <button
            onClick={handleAttachClick}
            style={chatbotStyles.attachButton}
            title="Attach files"
          >
            📎
          </button>
        )}

        <textarea
          value={input}
          placeholder={getChatbotText("placeholder")}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          style={{
            ...chatbotStyles.input,
            width: enableFileUpload && onFilesAttached ? "75%" : "85%",
          }}
        />
        {isLoading && onCancel ? (
          <button
            type="button"
            onClick={onCancel}
            style={chatbotStyles.sendButton("x")}
            aria-label="Cancel message"
          >
            Cancel
          </button>
        ) : (
          <button
            onClick={onSend}
            disabled={!canSend}
            style={chatbotStyles.sendButton(canSend ? "x" : "")}
          >
            {getChatbotText("sendMessage")}
          </button>
        )}
      </div>
    </div>
  );
};
