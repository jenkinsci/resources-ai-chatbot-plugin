import { getChatbotText } from '../data/chatbotTexts';
import { chatbotStyles } from '../styles/styles';

/**
 * Props for the Header component.
 */
interface HeaderProps {
  clearMessages: () => void;
}

/**
 * Header renders the top section of the chatbot panel, including the title and
 * a button to clear the current conversation. It receives a callback to handle
 * message clearing, typically triggered by user interaction.
 */
export const Header = ({ clearMessages }: HeaderProps) => (
  <div
    style={chatbotStyles.chatbotHeader}
  >
      <p>{getChatbotText('title')}</p>
      <button
        onClick={clearMessages}
        style={chatbotStyles.clearButton}
      >
        {getChatbotText("clearChat")}
    </button>
  </div>
);
