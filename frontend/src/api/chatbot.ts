import { type Message } from '../model/Message';
import { API_BASE_URL } from '../config';
import { getChatbotText } from '../data/chatbotTexts';
import { v4 as uuidv4 } from 'uuid';

/**
 * Send a request to the backend to create a new chat session and returns the id of the
 * chat session created.
 *
 * @returns A Promise resolving to the id of the new chat session
 */
export const createChatSession = async (): Promise<string> => {
  try{
    const response = await fetch(`${API_BASE_URL}/api/chatbot/sessions`, { method: 'POST' });
    const data = await response.json();

    return data.session_id;
  } catch (error) {
    console.error('Chatbot API error while creating a new chat session:', error);
    return "";
  }
};

/**
 * Sends the user's message to the backend chatbot API and returns the bot's response.
 * If the API call fails or returns an invalid response, a fallback error message is used.
 *
 * @param sessionId - The session id of the chat
 * @param userMessage - The message input from the user
 * @returns A Promise resolving to a bot-generated Message
 */
export const fetchChatbotReply = async (sessionId: string, userMessage: string): Promise<Message> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/chatbot/sessions/${sessionId}/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: userMessage }),
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();

    return createBotMessage(data.reply || getChatbotText('noResponseMessage'));
  } catch (error) {
    console.error('Chatbot API error while sending a message:', error);
    return createBotMessage(getChatbotText('errorMessage'));
  }
};

/**
 * Sends a request to the backend to delete the chat session with session id sessionId.
 *
 * @param sessionId - The session id of the chat to delete
 */
export const deleteChatSession = async (sessionId: string): Promise<void> => {
  try{
    await fetch(`${API_BASE_URL}/api/chatbot/sessions/${sessionId}`, { method: 'DELETE' });
  } catch(error) {
    console.error('Chatbot API error while deleting a chat session:', error);
  }
};

/**
 * Utility function to create a Message object from the bot,
 * using a UUID as the message ID.
 *
 * @param text - The text content of the bot's message
 * @returns A new Message object from the bot
 */
export const createBotMessage = (text: string): Message => ({
  id: uuidv4(),
  sender: 'jenkins-bot',
  text,
});
