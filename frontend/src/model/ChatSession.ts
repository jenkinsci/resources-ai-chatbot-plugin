import { type Message } from './Message';

/**
 * Repreesents a chat item, with its id, its messages and the date in which it was created.
 */
export interface ChatSession {
  id: string;
  messages: Message[];
  createdAt: string;
  isLoading: boolean;
}
