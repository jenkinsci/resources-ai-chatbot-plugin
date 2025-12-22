/**
 * Single message in the chatbot conversation.
 */
export interface Message {
  /** Unique identifier for the message (UUID) */
  id: string;
  sender: Sender |"user" | "assistant" | "bot";
  text: string;
}

/**
 * Represents the possible message senders in the chatbot interface.
 */
export type Sender = "user" | "jenkins-bot";
