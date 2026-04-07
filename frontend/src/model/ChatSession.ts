import { type Message } from "./Message";

/**
 * Repreesents a chat item, with its id, its messages and the date in which it was created.
 */
export interface ChatSession {
  id: string;
  messages: Message[];
  createdAt: string;
  isLoading: boolean;
  loadingStatus: string | null;
}

/**
 * Type guard to check if a given object is of the type ChatSession interface.
 */
export const isChatSession = (obj: unknown): obj is ChatSession => {
  if (typeof obj !== "object" || obj === null) {
    return false;
  }

  const o = obj as Record<string, unknown>;

  return (
    typeof o.id === "string" &&
    Array.isArray(o.messages) &&
    typeof o.createdAt === "string" &&
    typeof o.isLoading === "boolean" &&
    (typeof o.loadingStatus === "string" || o.loadingStatus === null)
  );
};
