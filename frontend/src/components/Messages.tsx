import React, { useEffect, useRef } from "react";
import {
  type Message,
  type Sender,
  type FileAttachment,
} from "../model/Message";
import { chatbotStyles } from "../styles/styles";
import { LoadingDots } from "./LoadingDots";

/**
 * Props for the Messages component.
 */
export interface MessagesProps {
  messages: Message[];
  isLoading: boolean;
  loadingStatus: string | null;
}

/**
 * Formats file size in human-readable format.
 */
const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

/**
 * Renders a file attachment display.
 */
const FileAttachmentDisplay: React.FC<{ file: FileAttachment }> = ({
  file,
}) => {
  if (file.type === "image" && file.previewUrl) {
    return (
      <div style={chatbotStyles.fileAttachmentContainer}>
        <img
          src={file.previewUrl}
          alt={file.filename}
          style={chatbotStyles.imagePreview}
        />
        <div style={chatbotStyles.fileAttachmentInfo}>
          <span style={chatbotStyles.fileAttachmentName}>{file.filename}</span>
          <span style={chatbotStyles.fileAttachmentSize}>
            {formatFileSize(file.size)}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div style={chatbotStyles.fileAttachmentContainer}>
      <div style={chatbotStyles.textFileIcon}>📄</div>
      <div style={chatbotStyles.fileAttachmentInfo}>
        <span style={chatbotStyles.fileAttachmentName}>{file.filename}</span>
        <span style={chatbotStyles.fileAttachmentSize}>
          {formatFileSize(file.size)}
        </span>
      </div>
    </div>
  );
};

/**
 * Messages is responsible for rendering the chat conversation thread,
 * including both user and bot messages. It also displays the loading message
 * message when the bot is generating a response and automatically scrolls
 * to the newest message on update.
 */
export const Messages = ({
  messages,
  isLoading,
  loadingStatus,
}: MessagesProps) => {
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const renderMessage = (
    text: string,
    sender: Sender,
    key: React.Key,
    files?: FileAttachment[],
  ) => (
    <div key={key} style={chatbotStyles.messageContainer(sender)}>
      <span style={chatbotStyles.messageBubble(sender)}>
        {/* Render file attachments if present */}
        {files && files.length > 0 && (
          <div style={chatbotStyles.messageFilesContainer}>
            {files.map((file, index) => (
              <FileAttachmentDisplay
                key={`${file.filename}-${index}`}
                file={file}
              />
            ))}
          </div>
        )}
        {/* Render text content */}
        {text.split("\n").map((line, i) => (
          <React.Fragment key={i}>
            {line}
            <br />
          </React.Fragment>
        ))}
      </span>
    </div>
  );

  return (
    <div style={chatbotStyles.messagesMain}>
      {messages.map((msg) =>
        renderMessage(msg.text, msg.sender, msg.id, msg.files),
      )}
      {isLoading && (
        <div style={chatbotStyles.botMessage}>
          <div style={chatbotStyles.loadingContainer}>
            <LoadingDots />
            <span style={chatbotStyles.loadingText}>{loadingStatus}</span>
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};
