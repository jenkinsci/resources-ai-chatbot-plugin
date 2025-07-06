import rawTexts from "./chatbotTexts.json";

/**
 * Retrieves a text from the chatbotTexts JSON file.
 *
 * @param key - The key corresponding to a chatbot message
 * @returns The associated message string
 */
export const getChatbotText = (key: keyof typeof rawTexts): string => {
  return rawTexts[key];
};
