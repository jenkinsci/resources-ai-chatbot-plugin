/**
 * Represents a file attachment in a message.
 */
export interface FileAttachment {
  /** Name of the file */
  filename: string;
  /** Type of file - "text" or "image" */
  type: "text" | "image";
  /** File size in bytes */
  size: number;
  /** MIME type of the file */
  mimeType: string;
  /** Preview URL for images (blob URL) */
  previewUrl?: string;
}

/**
 * Single message in the chatbot conversation.
 */
export interface Message {
  /** Unique identifier for the message (UUID) */
  id: string;
  sender: Sender;
  text: string;
  /** Optional file attachments */
  files?: FileAttachment[];
}

/**
 * Represents the possible message senders in the chatbot interface.
 */
export type Sender = "user" | "jenkins-bot";
