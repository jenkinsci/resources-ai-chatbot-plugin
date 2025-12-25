import type { KeyboardEvent } from "react";

import { getChatbotText } from "../data/chatbotTexts";
import { chatbotStyles } from "../styles/styles";

/**
 * Props for the Input component.
 */
export interface InputProps {
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  onCancel: () => void;
  loading: boolean;
}


/**
 * Input is a controlled textarea component for user message entry.
 * It supports multiline input and handles sending messages with Enter,
 * while allowing new lines with Shift+Enter.
 */
export const Input = ({ input, setInput, onSend, onCancel, loading }: InputProps) => {
  console.log("Input loading prop:", loading);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div style={chatbotStyles.inputContainer}>
      <textarea
        value={input}
        placeholder={getChatbotText("placeholder")}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={loading}
        style={chatbotStyles.input}
      />

      {loading && (
        <button
          onClick={onCancel}
          style={chatbotStyles.cancelButton()}
        >
          {getChatbotText("cancelMessage")}
        </button>
      )}
      {!loading && (
        <button
          onClick={onSend}
          disabled={!input.trim()}
          style={chatbotStyles.sendButton(input)}
        >
          {getChatbotText("sendMessage")}
        </button>
      )}

    </div>
  );
};