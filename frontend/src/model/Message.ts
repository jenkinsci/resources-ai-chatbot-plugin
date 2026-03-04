/**
 * Represents the type of file attachment.
 */
export const FILE_ATTACHMENT_TYPES = ["text", "image"] as const;

export type FileAttachmentType = (typeof FILE_ATTACHMENT_TYPES)[number];

/**
 * Represents a file attachment in a message.
 */
export interface FileAttachment {
  /** Name of the file */
  filename: string;
  /** Type of file */
  type: FileAttachmentType;
  /** File size in bytes */
  size: number;
  /** MIME type of the file */
  mimeType: string;
  /** Preview URL for images (blob URL) */
  previewUrl?: string;
}

/**
 * Type guard to check if a given object is of the type FileAttachment interface.
 */
export const isFileAttachment = (obj: unknown): obj is FileAttachment => {
  if (typeof obj !== "object" || obj === null) {
    return false;
  }

  const o = obj as Record<string, unknown>;

  return (
    typeof o.filename === "string" &&
    FILE_ATTACHMENT_TYPES.includes(o.type as any) &&
    typeof o.size === "number" &&
    typeof o.mimeType === "string" &&
    (o.previewUrl === undefined || typeof o.previewUrl === "string")
  );
};

/**
 * Represents the possible message senders in the chatbot interface.
 */
export const SENDERS = ["user", "jenkins-bot"] as const;
/**
 * Represents the possible message senders in the chatbot interface.
 */
export type Sender = (typeof SENDERS)[number];

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
 * Type guard to check if a given object is of the type Message interface.
 */
export const isMessage = (obj: unknown): obj is Message => {
  if (typeof obj !== "object" || obj === null) {
    return false;
  }

  const o = obj as Record<string, unknown>;

  return (
    typeof o.id === "string" &&
    SENDERS.includes(o.sender as any) &&
    typeof o.text === "string" &&
    (o.files === undefined ||
      (Array.isArray(o.files) && o.files.every(isFileAttachment)))
  );
};
