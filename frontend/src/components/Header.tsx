import { getChatbotText } from "../data/chatbotTexts";
import { chatbotStyles } from "../styles/styles";
import {
  exportAsTxt,
  exportAsMd,
  exportAsDocx,
  exportAsPdf,
} from "../utils/exportchat";
import { type Message } from "../model/Message";
import { useEffect, useRef, useState } from "react";
import {
  Upload,
  Trash2,
  FileText,
  FileCode,
  FileSpreadsheet,
  File,
} from "lucide-react";

/**
 * Props for the Header component.
 */
export interface HeaderProps {
  currentSessionId: string | null;
  isBackendConnected: boolean;
  lastBackendCheck?: Date | null;
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
  isBackendConnected,
  lastBackendCheck = null,
  clearMessages,
  openSideBar,
  messages,
}: HeaderProps) => {
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showBackendStatusTooltip, setShowBackendStatusTooltip] =
    useState(false);
  const exportMenuRef = useRef<HTMLDivElement | null>(null);
  const lastCheckedLabel = lastBackendCheck
    ? `${getChatbotText("lastChecked")} ${lastBackendCheck.toLocaleTimeString()}`
    : getChatbotText("lastCheckPending");

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        showExportMenu &&
        exportMenuRef.current &&
        !exportMenuRef.current.contains(event.target as Node)
      ) {
        setShowExportMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showExportMenu]);

  return (
    <div style={chatbotStyles.chatbotHeader}>
      <div style={chatbotStyles.headerLeading}>
        <button
          onClick={openSideBar}
          style={chatbotStyles.openSidebarButton}
          aria-label="Toggle sidebar"
        >
          {getChatbotText("sidebarLabel")}
        </button>
        <span
          style={chatbotStyles.backendStatusContainer}
          onMouseEnter={() => setShowBackendStatusTooltip(true)}
          onMouseLeave={() => setShowBackendStatusTooltip(false)}
          onFocus={() => setShowBackendStatusTooltip(true)}
          onBlur={() => setShowBackendStatusTooltip(false)}
          tabIndex={0}
          aria-label={
            isBackendConnected
              ? getChatbotText("backendConnected")
              : getChatbotText("backendNotConnected")
          }
        >
          <span style={chatbotStyles.backendStatusDot(isBackendConnected)} />
          {showBackendStatusTooltip && (
            <span role="tooltip" style={chatbotStyles.backendStatusTooltip}>
              <span>
                {isBackendConnected
                  ? getChatbotText("backendConnected")
                  : getChatbotText("backendNotConnected")}
              </span>
              <span>{lastCheckedLabel}</span>
            </span>
          )}
        </span>
      </div>
      {currentSessionId !== null && (
        <div ref={exportMenuRef} style={chatbotStyles.headerActions}>
          <div style={{ position: "relative", display: "inline-block" }}>
            {/* Export button */}
            <button
              onClick={() => setShowExportMenu((prev) => !prev)}
              style={chatbotStyles.exportButton}
              title="Export chat"
              aria-label="Export chat"
            >
              <Upload size={16} />
            </button>

            {/* Export menu */}
            {showExportMenu && (
              <div style={chatbotStyles.exportMenu}>
                <button
                  style={chatbotStyles.exportMenuItem}
                  onClick={() => {
                    exportAsTxt(messages);
                    setShowExportMenu(false);
                  }}
                >
                  <FileText size={20} />
                  <span>.txt</span>
                </button>
                <button
                  style={chatbotStyles.exportMenuItem}
                  onClick={() => {
                    exportAsMd(messages);
                    setShowExportMenu(false);
                  }}
                >
                  <FileCode size={20} />
                  <span>.md</span>
                </button>
                <button
                  style={chatbotStyles.exportMenuItem}
                  onClick={() => {
                    exportAsDocx(messages);
                    setShowExportMenu(false);
                  }}
                >
                  <FileSpreadsheet size={20} />
                  <span>.docx</span>
                </button>
                <button
                  style={chatbotStyles.exportMenuItem}
                  onClick={() => {
                    exportAsPdf(messages);
                    setShowExportMenu(false);
                  }}
                >
                  <File size={20} />
                  <span>.pdf</span>
                </button>
              </div>
            )}
          </div>

          <button
            onClick={() => clearMessages(currentSessionId)}
            style={chatbotStyles.clearButton}
            title="Clear chat"
            aria-label="Clear chat"
          >
            <Trash2 size={16} />
          </button>
        </div>
      )}
    </div>
  );
};
