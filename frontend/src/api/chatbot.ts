import { type Message, type FileAttachment } from "../model/Message";
import { getChatbotText } from "../data/chatbotTexts";
import { v4 as uuidv4 } from "uuid";
import { CHATBOT_API_TIMEOUTS_MS, API_BASE_URL } from "../config";
import { callChatbotApi } from "../utils/callChatbotApi";

/**
 * Supported file extensions response from the backend.
 */
export interface SupportedExtensions {
  text: string[];
  image: string[];
  max_text_size_mb: number;
  max_image_size_mb: number;
}

/**
 * Send a request to the backend to create a new chat session and returns the id of the
 * chat session created.
 *
 * @returns A Promise resolving to the id of the new chat session
 */
export const createChatSession = async (): Promise<string> => {
  const data = await callChatbotApi<{ session_id: string }>(
    "sessions",
    { method: "POST" },
    { session_id: "" },
    CHATBOT_API_TIMEOUTS_MS.CREATE_SESSION,
  );

  if (!data.session_id) {
    console.error(
      "Failed to create chat session: session_id missing in response",
      data,
    );
    return "";
  }

  return data.session_id;
};
/**
 * Sends the user's message to the backend chatbot API and returns the bot's response.
 * If the API call fails or returns an invalid response, a fallback error message is used.
 *
 * @param sessionId - The session id of the chat
 * @param userMessage - The message input from the user
 * @returns A Promise resolving to a bot-generated Message
 */
export const fetchChatbotReply = async (
  sessionId: string,
  userMessage: string,
): Promise<Message> => {
  const data = await callChatbotApi<{ reply?: string }>(
    `sessions/${sessionId}/message`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMessage }),
    },
    {},
    CHATBOT_API_TIMEOUTS_MS.GENERATE_MESSAGE,
  );

  const botReply = data.reply || getChatbotText("errorMessage");
  return createBotMessage(botReply);
};

/**
 * Sends the user's message with file attachments to the backend chatbot API.
 * Uses multipart/form-data to upload files along with the message.
 *
 * @param sessionId - The session id of the chat
 * @param userMessage - The message input from the user
 * @param files - Array of File objects to upload
 * @returns A Promise resolving to a bot-generated Message
 */
export const fetchChatbotReplyWithFiles = async (
  sessionId: string,
  userMessage: string,
  files: File[],
): Promise<Message> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(
    () => controller.abort(),
    CHATBOT_API_TIMEOUTS_MS.GENERATE_MESSAGE,
  );

  try {
    const formData = new FormData();
    formData.append("message", userMessage);

    files.forEach((file) => {
      formData.append("files", file);
    });

    const response = await fetch(
      `${API_BASE_URL}/api/chatbot/sessions/${sessionId}/message/upload`,
      {
        method: "POST",
        body: formData,
        signal: controller.signal,
      },
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.detail || `HTTP error: ${response.status}`;
      console.error(`API error: ${response.status} - ${errorMessage}`);
      return createBotMessage(getChatbotText("errorMessage"));
    }

    const data = await response.json();
    const botReply = data.reply || getChatbotText("errorMessage");
    return createBotMessage(botReply);
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      console.error(
        `API request timed out after ${CHATBOT_API_TIMEOUTS_MS.GENERATE_MESSAGE}ms`,
      );
    } else {
      console.error("API error uploading files:", error);
    }
    return createBotMessage(getChatbotText("errorMessage"));
  } finally {
    clearTimeout(timeoutId);
  }
};

/**
 * Fetches the list of supported file extensions from the backend.
 *
 * @returns A Promise resolving to the supported extensions or null if failed
 */
export const fetchSupportedExtensions =
  async (): Promise<SupportedExtensions | null> => {
    try {
      const data = await callChatbotApi<SupportedExtensions>(
        "files/supported-extensions",
        { method: "GET" },
        { text: [], image: [], max_text_size_mb: 5, max_image_size_mb: 10 },
        CHATBOT_API_TIMEOUTS_MS.CREATE_SESSION,
      );
      return data;
    } catch (error) {
      console.error("Failed to fetch supported extensions:", error);
      return null;
    }
  };

/**
 * Sends a request to the backend to delete the chat session with session id sessionId.
 *
 * @param sessionId - The session id of the chat to delete
 */
export const deleteChatSession = async (sessionId: string): Promise<void> => {
  await callChatbotApi<void>(
    `sessions/${sessionId}`,
    { method: "DELETE" },
    undefined,
    CHATBOT_API_TIMEOUTS_MS.DELETE_SESSION,
  );
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
  sender: "jenkins-bot",
  text,
});

/**
 * Converts a File object to a FileAttachment for display purposes.
 *
 * @param file - The File object to convert
 * @returns A FileAttachment object
 */
export const fileToAttachment = (file: File): FileAttachment => {
  const isImage = file.type.startsWith("image/");
  return {
    filename: file.name,
    type: isImage ? "image" : "text",
    size: file.size,
    mimeType: file.type || "application/octet-stream",
    previewUrl: isImage ? URL.createObjectURL(file) : undefined,
  };
};

/**
 * Validates if a file is supported for upload.
 *
 * @param file - The file to validate
 * @param supportedExtensions - The supported extensions config
 * @returns An object with isValid boolean and optional error message
 */
export const validateFile = (
  file: File,
  supportedExtensions?: SupportedExtensions | null,
): { isValid: boolean; error?: string } => {
  if (!supportedExtensions) {
    // Default validation if extensions not loaded
    const maxSize = 10 * 1024 * 1024; // 10 MB
    if (file.size > maxSize) {
      return { isValid: false, error: `File exceeds maximum size of 10 MB` };
    }
    return { isValid: true };
  }

  const extension = "." + file.name.split(".").pop()?.toLowerCase();
  const isTextFile = supportedExtensions.text.indexOf(extension) !== -1;
  const isImageFile = supportedExtensions.image.indexOf(extension) !== -1;

  if (!isTextFile && !isImageFile) {
    return {
      isValid: false,
      error: `Unsupported file type: ${extension}`,
    };
  }

  const maxSizeMb = isImageFile
    ? supportedExtensions.max_image_size_mb
    : supportedExtensions.max_text_size_mb;
  const maxSizeBytes = maxSizeMb * 1024 * 1024;

  if (file.size > maxSizeBytes) {
    return {
      isValid: false,
      error: `File exceeds maximum size of ${maxSizeMb} MB`,
    };
  }

  return { isValid: true };
};
