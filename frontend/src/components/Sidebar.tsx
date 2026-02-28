import type { ChatSession } from "../model/ChatSession";
import { chatbotStyles } from "../styles/styles";
import { getChatbotText } from "../data/chatbotTexts";
import { Plus, X, Trash2, MessageSquare } from "lucide-react";

/**
 * Props for the Sidebar component.
 */
export interface SidebarProps {
  onClose: () => void;
  onCreateChat: () => void;
  onSwitchChat: (chatSessionId: string) => void;
  openConfirmDeleteChatPopup: (chatSessionId: string) => void;
  chatList: ChatSession[];
  activeChatId: string | null;
}

/**
 * Sidebar renders the sidebar section of the chatbot UI, including the button to
 * create new chats, and the list of active chats.
 */
export const Sidebar = ({
  onClose,
  onCreateChat,
  onSwitchChat,
  openConfirmDeleteChatPopup,
  chatList,
  activeChatId,
}: SidebarProps) => {
  const getChatName = (chat: ChatSession, index: number) => {
    if (chat.messages.length > 0) {
      const firstMessage = chat.messages[0].text;
      return firstMessage.length > 25
        ? `${firstMessage.slice(0, 25).trim()}...`
        : firstMessage;
    }

    return `Chat ${index + 1}`;
  };

  return (
    <div style={chatbotStyles.sidebarContainer}>
      <div style={chatbotStyles.sidebarHeader}>
        <div style={chatbotStyles.sidebarTitle}>History</div>
        <button onClick={onClose} style={chatbotStyles.sidebarCloseButton} aria-label="Close sidebar">
          <X size={18} />
        </button>
      </div>

      <div style={chatbotStyles.sidebarContent}>
        <button
          onClick={() => {
            onClose();
            onCreateChat();
          }}
          style={chatbotStyles.sidebarCreateNewChatButton}
        >
          <Plus size={16} />
          <span>{getChatbotText("sidebarCreateNewChat")}</span>
        </button>

        <div style={chatbotStyles.sidebarListChatsContainer}>
          {chatList.length === 0 ? (
            <p style={chatbotStyles.sidebarNoChatsText}>
              {getChatbotText("sidebarNoActiveChats")}
            </p>
          ) : (
            chatList.map((chat, index) => {
              const isActive = chat.id === activeChatId;
              return (
                <div
                  key={chat.id}
                  onClick={() => onSwitchChat(chat.id)}
                  style={chatbotStyles.sidebarChatContainer(isActive)}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flex: 1, overflow: "hidden" }}>
                    <MessageSquare size={14} color={isActive ? "var(--primary-color)" : "var(--text-secondary)"} />
                    <span style={chatbotStyles.sidebarChatTitle}>
                      {getChatName(chat, index)}
                    </span>
                  </div>
                  <button
                    style={chatbotStyles.sidebarDeleteChatButton}
                    className="delete-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      openConfirmDeleteChatPopup(chat.id);
                    }}
                    aria-label="Delete Chat"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
