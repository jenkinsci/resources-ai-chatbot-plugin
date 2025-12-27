import { getChatbotText } from "../data/chatbotTexts";
import { chatbotStyles } from "../styles/styles";
import {
  exportAsTxt,
  exportAsMd,
  exportAsDocx,
  exportAsPdf,
} from "../utils/exportchat";
import { type Message } from "../model/Message";
import { useState } from "react";
import { Upload } from "lucide-react";

/**
 * Props for the Header component.
 */
export interface HeaderProps {
  currentSessionId: string | null;
  clearMessages: (chatSessionId: string) => void;
  openSideBar: () => void;
  messages: Message[];
}

/**
 * Header renders the top section of the chatbot panel, including the title and
 * a button to clear the current conversation. It receives a callback to handle
 * message clearing, typically triggered by user interaction.
 */
export const Header = ({
  currentSessionId,
  clearMessages,
  openSideBar,
  messages,
}: HeaderProps) => {

  const [showExportMenu, setShowExportMenu] = useState(false);

  return (
    <div style={chatbotStyles.chatbotHeader}>
      <button
        onClick={openSideBar}
        style={chatbotStyles.openSidebarButton}
        aria-label="Toggle sidebar"
      >
        {getChatbotText("sidebarLabel")}
      </button>
      {currentSessionId !== null && (
        <div style={chatbotStyles.headerActions}>
        <div style={{ position: "relative", display: "inline-block" }}>
          {/* Export button */}
          <button
          onClick={() => setShowExportMenu((prev) => !prev)}
          style={chatbotStyles.clearButton}
          title="Export text"
          aria-label="Export chat"
          >
            <Upload size={16} />
          </button>

          {/* Export menu */}
          {showExportMenu && (
            <div style={chatbotStyles.exportMenu}>
              <button onClick={() => { exportAsTxt(messages); setShowExportMenu(false); }}>.txt</button>
              <button onClick={() => { exportAsMd(messages); setShowExportMenu(false); }}>.md</button>
              <button onClick={() => { exportAsDocx(messages); setShowExportMenu(false); }}>.docx</button>
              <button onClick={() => { exportAsPdf(messages); setShowExportMenu(false); }}>.pdf</button>
            </div>
          )}
        </div>

        <button
          onClick={() => clearMessages(currentSessionId)}
          style={chatbotStyles.clearButton}
        >
          {getChatbotText("clearChat")}
        </button></div>
      )}
    </div>
  );
};
