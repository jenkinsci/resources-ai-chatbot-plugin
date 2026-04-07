import type { ChatSession } from "../model/ChatSession";
import { chatbotStyles } from "../styles/styles";
import { getChatbotText } from "../data/chatbotTexts";

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
      <div style={chatbotStyles.sidebarCloseButtonContainer}>
        <button onClick={onClose} style={chatbotStyles.sidebarCloseButton}>
          &times;
        </button>
      </div>

      <button
        onClick={() => {
          onClose();
          onCreateChat();
        }}
        aria-label="Close Sidebar"
        style={chatbotStyles.sidebarCreateNewChatButton}
      >
        {getChatbotText("sidebarCreateNewChat")}
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
                {getChatName(chat, index)}
                <button
                  style={chatbotStyles.sidebarDeleteChatButton}
                  onClick={(e) => {
                    e.stopPropagation();
                    openConfirmDeleteChatPopup(chat.id);
                  }}
                  aria-label="Delete Chat"
                >
                  &#128465;
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
