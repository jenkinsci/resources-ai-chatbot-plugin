import { type Message } from '../model/Message';
import { API_BASE_URL } from '../config';
import { getChatbotText } from '../data/chatbotTexts';
import { v4 as uuidv4 } from 'uuid';

/**
 * Sends the user's message to the backend chatbot API and returns the bot's response.
 * If the API call fails or returns an invalid response, a fallback error message is used.
 *
 * @param userMessage - The message input from the user
 * @returns A Promise resolving to a bot-generated Message
 */
export const fetchChatbotReply = async (userMessage: string): Promise<Message> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/chatbot/reply`, {
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
    console.error('Chatbot API error:', error);
    return createBotMessage(getChatbotText('errorMessage'));
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
