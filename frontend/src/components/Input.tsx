import { useRef, useState, useEffect } from "react";
import { getChatbotText } from "../data/chatbotTexts";
import {
  Paperclip,
  Send,
  CircleStop,
  File,
  AlertTriangle,
  X,
} from "lucide-react";

export interface InputProps {
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  attachedFiles?: File[];
  onFilesAttached?: (files: File[]) => void;
  onFileRemoved?: (index: number) => void;
  enableFileUpload?: boolean;
  validateFile?: (file: File) => { isValid: boolean; error?: string };
  isLoading?: boolean;
  onCancel?: () => void;
}

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
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Auto-clear validation error after 5 seconds
  useEffect(() => {
    if (validationError) {
      const timer = setTimeout(() => setValidationError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [validationError]);

  // Adjust textarea height automatically based on content length
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const handleFileSelect = (files: FileList) => {
    if (!files || files.length === 0 || !onFilesAttached) return;

    const validFiles: File[] = [];
    const errors: string[] = [];

    Array.from(files).forEach((file: File) => {
      const isDuplicate = attachedFiles.some(
        (existing) => existing.name === file.name && existing.size === file.size
      );
      if (isDuplicate) {
        errors.push(`${file.name} is already attached.`);
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
      setValidationError(errors.join(" "));
    }
    if (validFiles.length > 0) {
      onFilesAttached([...attachedFiles, ...validFiles]);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files) {
      handleFileSelect(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
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
    <div
      className="chatbot-input-wrapper"
      onDragOver={enableFileUpload ? handleDragOver : undefined}
      onDragLeave={enableFileUpload ? handleDragLeave : undefined}
      onDrop={enableFileUpload ? handleDrop : undefined}
    >
      {/* Drag & Drop Overlay */}
      {isDragOver && enableFileUpload && (
        <div className="drag-drop-overlay">
          <div className="drag-drop-message">
            <span>Drop files to attach</span>
          </div>
        </div>
      )}

      {/* Validation Error Banner */}
      {validationError && (
        <div className="validation-error-banner">
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <AlertTriangle size={14} />
            <span>{validationError}</span>
          </div>
          <button
            className="validation-close-btn"
            onClick={() => setValidationError(null)}
          >
            &times;
          </button>
        </div>
      )}

      {/* Attached Files List Previews */}
      {attachedFiles.length > 0 && (
        <div className="attached-files-preview-container">
          {attachedFiles.map((file, index) => {
            const isImage = file.type.startsWith("image/");
            return (
              <div key={`${file.name}-${index}`} className="attached-file-chip">
                {isImage ? (
                  <img
                    src={URL.createObjectURL(file)}
                    alt={file.name}
                    data-testid="file-icon-image"
                    className="attached-chip-thumbnail"
                  />
                ) : (
                  <span className="attached-chip-icon" data-testid="file-icon-document">
                    <File size={12} />
                  </span>
                )}
                <span className="attached-chip-name" title={`${file.name} (${formatFileSize(file.size)})`}>
                  {file.name} ({formatFileSize(file.size)})
                </span>
                {onFileRemoved && (
                  <button
                    onClick={() => onFileRemoved(index)}
                    className="attached-chip-remove"
                    title="Remove file"
                  >
                    <X size={10} />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Main input bar area */}
      <div className="chatbot-input-bar">
        {/* Hidden file input */}
        {enableFileUpload && (
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={(e) => handleFileSelect(e.target.files!)}
            style={{ display: "none" }}
            accept=".txt,.log,.md,.json,.xml,.yaml,.yml,.py,.js,.ts,.tsx,.java,.groovy,.sh,.png,.jpg,.jpeg,.gif,.webp,.bmp"
            aria-label="Upload files"
          />
        )}

        {/* Paperclip attachment button */}
        {enableFileUpload && onFilesAttached && (
          <button
            className="chatbot-input-button"
            onClick={handleAttachClick}
            title="Attach files"
            aria-label="Attach files"
          >
            <Paperclip size={16} />
          </button>
        )}

        <textarea
          ref={textareaRef}
          value={input}
          placeholder={getChatbotText("placeholder")}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className="chatbot-input-textarea"
          rows={1}
          aria-label="Chat input field"
        />

        {isLoading && onCancel ? (
          <button
            type="button"
            onClick={onCancel}
            className="chatbot-input-button send-active"
            aria-label="Cancel message generation"
            title="Cancel generation"
          >
            <CircleStop size={18} />
          </button>
        ) : (
          <button
            onClick={onSend}
            disabled={!canSend}
            className={`chatbot-input-button ${canSend ? "send-active" : ""}`}
            aria-label="Send message"
            title="Send message"
          >
            <Send size={16} />
          </button>
        )}
      </div>

      <div className="chatbot-input-footer-caption">
        Predictive system analysis based on build history
      </div>
    </div>
  );
};
