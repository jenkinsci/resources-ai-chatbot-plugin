import { getChatbotText } from '../data/chatbotTexts';
import { chatbotStyles } from '../styles/styles';

/**
 * Props for the Header component.
 */
interface HeaderProps {
  isChat: boolean;
  clearMessages: () => void;
  openSideBar: () => void;
}

/**
 * Header renders the top section of the chatbot panel, including the title and
 * a button to clear the current conversation. It receives a callback to handle
 * message clearing, typically triggered by user interaction.
 */
export const Header = ({ isChat, clearMessages, openSideBar }: HeaderProps) => {
  return(
  <div
    style={chatbotStyles.chatbotHeader}
  >
      <button
        onClick={openSideBar}
        style={chatbotStyles.openSidebarButton}
        aria-label="Toggle sidebar"
      >
        {getChatbotText("sidebarLabel")}
      </button>
      {isChat && 
      <button
        onClick={clearMessages}
        style={chatbotStyles.clearButton}
      >
        {getChatbotText("clearChat")}
      </button>
      }
  </div>
)};
