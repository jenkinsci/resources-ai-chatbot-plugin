import { useEffect, useRef, useState } from "react";
import { type Message } from "../model/Message";
import { exportAsTxt, exportAsMd, exportAsDocx, exportAsPdf } from "../utils/exportchat";
import {
  Download,
  Trash2,
  X,
  Sun,
  Moon,
  FileText,
  FileCode,
  FileSpreadsheet,
  File,
} from "lucide-react";

export interface HeaderProps {
  currentSessionId: string | null;
  clearMessages: (chatSessionId: string) => void;
  messages: Message[];
  isDark: boolean;
  setIsDark: (dark: boolean) => void;
  onClose: () => void;
}

export const Header = ({
  currentSessionId,
  clearMessages,
  messages,
  isDark,
  setIsDark,
  onClose,
}: HeaderProps) => {
  const [showExportMenu, setShowExportMenu] = useState(false);
  const exportMenuRef = useRef<HTMLDivElement | null>(null);

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
    <div className="chatbot-header">
      <div className="header-brand-container">
        <img
          alt="Jenkins AI Logo"
          className={`header-logo ${isDark ? "dark-logo" : ""}`}
          src="https://lh3.googleusercontent.com/aida-public/AB6AXuBD-X7_6zh-ve42nEMOBvzUZNAGW5qZCOPJoNux3Sox9zhpFT0_yvHAvb0fevBzZVypWMKePiD14uHvXtDbp4nK8a-_v6Wa2zgzbj5iHLjH4TgihzAZXVpx8oYgRJlEBhd21CBwOVCqsE1SLQL-9JDU4ou12kT2yZ_g09-4aHn34jOJRIwGcCh4VuMrLwAvPbPjE3mNTSM2CO9uZa-MJCho1OSmjOr6rG6LEHjl8CJ_sJHOHXNDIDQx0BEoY1GcxcWYNC0IuTk2bn1G"
        />
        <div className="header-title-wrapper">
          <h3 className="header-title">JENKINS ASSISTANT</h3>
          <div className="header-status-wrapper">
            <span className="status-dot"></span>
            <span className="header-status-text">Active System Analysis</span>
          </div>
        </div>
      </div>

      <div className="header-actions">
        {/* Dark/Light mode toggle */}
        <button
          className="header-action-button"
          onClick={() => setIsDark(!isDark)}
          title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
          aria-label="Toggle Theme"
        >
          {isDark ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {currentSessionId !== null && (
          <>
            {/* Export options menu */}
            <div ref={exportMenuRef} className="export-menu-container">
              <button
                className="header-action-button"
                onClick={() => setShowExportMenu((prev) => !prev)}
                title="Export chat history"
                aria-label="Export chat history"
              >
                <Download size={16} />
              </button>
              {showExportMenu && (
                <div className="export-menu">
                  <button
                    className="export-menu-item"
                    onClick={() => {
                      exportAsTxt(messages);
                      setShowExportMenu(false);
                    }}
                  >
                    <FileText size={14} />
                    <span>.txt</span>
                  </button>
                  <button
                    className="export-menu-item"
                    onClick={() => {
                      exportAsMd(messages);
                      setShowExportMenu(false);
                    }}
                  >
                    <FileCode size={14} />
                    <span>.md</span>
                  </button>
                  <button
                    className="export-menu-item"
                    onClick={() => {
                      exportAsDocx(messages);
                      setShowExportMenu(false);
                    }}
                  >
                    <FileSpreadsheet size={14} />
                    <span>.docx</span>
                  </button>
                  <button
                    className="export-menu-item"
                    onClick={() => {
                      exportAsPdf(messages);
                      setShowExportMenu(false);
                    }}
                  >
                    <File size={14} />
                    <span>.pdf</span>
                  </button>
                </div>
              )}
            </div>

            {/* Clear messages (deletes current chat) */}
            <button
              className="header-action-button"
              onClick={() => clearMessages(currentSessionId)}
              title="Delete chat session"
              aria-label="Delete chat session"
            >
              <Trash2 size={16} />
            </button>
          </>
        )}

        {/* Close Chat widget control */}
        <button
          className="header-action-button"
          onClick={onClose}
          title="Close chat widget"
          aria-label="Close Chat"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
};
