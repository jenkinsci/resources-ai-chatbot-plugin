import React, { useEffect, useRef } from "react";
import {
  type Message,
  type Sender,
  type FileAttachment,
} from "../model/Message";
import { Bot, User, File } from "lucide-react";

export interface MessagesProps {
  messages: Message[];
  isLoading: boolean;
  loadingStatus: string | null;
}

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const FileAttachmentDisplay: React.FC<{ file: FileAttachment }> = ({ file }) => {
  if (file.type === "image" && file.previewUrl) {
    return (
      <div className="file-attachment-card">
        <img
          src={file.previewUrl}
          alt={file.filename}
          className="file-attachment-preview"
        />
        <div className="file-attachment-details">
          <span className="file-attachment-name">{file.filename}</span>
          <span className="file-attachment-size">
            {formatFileSize(file.size)}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="file-attachment-card">
      <div className="file-attachment-icon">
        <File size={18} />
      </div>
      <div className="file-attachment-details">
        <span className="file-attachment-name">{file.filename}</span>
        <span className="file-attachment-size">
          {formatFileSize(file.size)}
        </span>
      </div>
    </div>
  );
};

// Formats message text with markdown code blocks, inline code, and bold text tags
const formatMessageText = (text: string): React.ReactNode => {
  if (!text) return null;

  // Split content by code blocks (```code```)
  const parts = text.split(/(```[\s\S]*?```)/g);
  return parts.map((part, index) => {
    if (part.startsWith("```") && part.endsWith("```")) {
      const content = part.slice(3, -3).trim();
      const lines = content.split("\n");
      const firstLine = lines[0].trim();
      const hasLanguage = /^[a-zA-Z0-9_-]+$/.test(firstLine);
      const codeContent = hasLanguage ? lines.slice(1).join("\n") : content;

      return (
        <pre key={index}>
          <code>{codeContent}</code>
        </pre>
      );
    }

    // Split sub-part by inline code (`code`), bold (**text**), or HTML style <strong> tags
    const inlineParts = part.split(/(`[^`]+`|\*\*[^*]+\*\*|<strong>[^<]+<\/strong>)/g);
    const renderedInline = inlineParts.map((subPart, subIndex) => {
      if (subPart.startsWith("`") && subPart.endsWith("`")) {
        return <code key={subIndex}>{subPart.slice(1, -1)}</code>;
      }
      if (subPart.startsWith("**") && subPart.endsWith("**")) {
        return <strong key={subIndex}>{subPart.slice(2, -2)}</strong>;
      }
      if (subPart.startsWith("<strong>") && subPart.endsWith("</strong>")) {
        return <strong key={subIndex}>{subPart.slice(8, -9)}</strong>;
      }

      // Handle standard newlines
      const lines = subPart.split("\n");
      return lines.map((line, lineIndex) => (
        <React.Fragment key={`${subIndex}-${lineIndex}`}>
          {line}
          {lineIndex < lines.length - 1 && <br />}
        </React.Fragment>
      ));
    });

    return <span key={index}>{renderedInline}</span>;
  });
};

export const Messages = ({
  messages,
  isLoading,
  loadingStatus,
}: MessagesProps) => {
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const renderMessage = (
    text: string,
    sender: Sender,
    key: React.Key,
    files?: FileAttachment[]
  ) => {
    const isUser = sender === "user";
    return (
      <div key={key} className={`message-row ${isUser ? "user-row" : "bot-row"}`}>
        <div className={`message-avatar ${isUser ? "user-avatar" : "bot-avatar"}`}>
          {isUser ? <User size={16} /> : <Bot size={16} />}
        </div>
        <div className="message-content-wrapper">
          {/* Render file attachments if present */}
          {files && files.length > 0 && (
            <div className="message-files-container">
              {files.map((file, index) => (
                <FileAttachmentDisplay
                  key={`${file.filename}-${index}`}
                  file={file}
                />
              ))}
            </div>
          )}
          {/* Render text bubble */}
          <div className="message-bubble">
            {formatMessageText(text)}
          </div>
        </div>
      </div>
    );
  };

  const isLogAnalysis =
    loadingStatus?.toLowerCase().includes("analyzing stack trace") ||
    loadingStatus?.toLowerCase().includes("analyzing logs") ||
    loadingStatus?.toLowerCase().includes("stack trace");

  return (
    <div className="chat-messages-container" id="chat-body">
      {messages.length === 0 && !isLoading && (
        <div className="welcome-screen-container">
          <div className="welcome-avatar-wrapper">
            <img
              alt="Jenkins Logo"
              className="welcome-logo"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuBD-X7_6zh-ve42nEMOBvzUZNAGW5qZCOPJoNux3Sox9zhpFT0_yvHAvb0fevBzZVypWMKePiD14uHvXtDbp4nK8a-_v6Wa2zgzbj5iHLjH4TgihzAZXVpx8oYgRJlEBhd21CBwOVCqsE1SLQL-9JDU4ou12kT2yZ_g09-4aHn34jOJRIwGcCh4VuMrLwAvPbPjE3mNTSM2CO9uZa-MJCho1OSmjOr6rG6LEHjl8CJ_sJHOHXNDIDQx0BEoY1GcxcWYNC0IuTk2bn1G"
            />
          </div>
          <h2 className="welcome-title">How can I assist your builds today?</h2>
          <p className="welcome-desc">
            Ask me anything to optimize your pipelines, check plugin compatibility, or analyze build errors.
          </p>
        </div>
      )}

      {messages.map((msg) =>
        renderMessage(msg.text, msg.sender, msg.id, msg.files)
      )}

      {/* AI loading / generating / workflow stages state */}
      {isLoading && (
        <div className="message-row bot-row">
          <div className="message-avatar bot-avatar">
            <Bot size={16} />
          </div>
          <div className="message-content-wrapper">
            {isLogAnalysis ? (
              <div className="ai-loading-container">
                <div className="workflow-steps-list">
                  <div className="workflow-step-line">
                    Analyzing build logs...
                  </div>
                  <div className="workflow-step-line" style={{ animationDelay: "0.8s" }}>
                    Checking plugin compatibility...
                  </div>
                  <div className="workflow-step-line" style={{ animationDelay: "1.6s" }}>
                    Formulating declarative fix...
                  </div>
                </div>
              </div>
            ) : (
              <div className="spinner-text-wrapper">
                <span className="subtle-spinner"></span>
                <span>{loadingStatus || "Generating response..."}</span>
              </div>
            )}
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};
