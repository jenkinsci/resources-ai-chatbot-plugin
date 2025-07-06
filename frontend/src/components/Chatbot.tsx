import { useState, useEffect } from "react";
import { type Message } from "../model/Message";
import { type ChatSession } from "../model/ChatSession";
import {
  fetchChatbotReply,
  createChatSession,
  deleteChatSession,
} from "../api/chatbot";
import { Header } from "./Header";
import { Messages } from "./Messages";
import { Sidebar } from "./Sidebar";
import { Input } from "./Input";
import { chatbotStyles } from "../styles/styles";
import { getChatbotText } from "../data/chatbotTexts";
import {
  loadChatbotSessions,
  loadChatbotLastSessionId,
} from "../utils/chatbotStorage";
import { v4 as uuidv4 } from "uuid";

/**
 * Chatbot is the core component responsible for managing the chatbot display.
 */
export const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [sessions, setSessions] = useState<ChatSession[]>(loadChatbotSessions);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(
    loadChatbotLastSessionId,
  );
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isPopupOpen, setIsPopupOpen] = useState<boolean>(false);
  const [sessionIdToDelete, setSessionIdToDelete] = useState<string | null>(
    null,
  );

  /**
   * Saving the chat sessions in the session storage only
   * when the component unmounts to avoid continuos savings.
   */
  useEffect(() => {
    const handleBeforeUnload = () => {
      sessionStorage.setItem("chatbot-sessions", JSON.stringify(sessions));
      sessionStorage.setItem("chatbot-last-session-id", currentSessionId || "");
    };

    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [sessions, currentSessionId]);

  /**
   * Returns the messages of a chat session.
   * @param sessionId The sessionId of the chat session.
   * @returns The messages of the chat with id equals to sessionId
   */
  const getSessionMessages = (sessionId: string | null) => {
    if (currentSessionId === null) {
      console.error("No current session");
      return [];
    }
    const chatSession = sessions.find((item) => item.id === sessionId);

    if (chatSession) {
      return chatSession.messages;
    }

    console.error(`No session found with sessionId ${sessionId}`);
    return [];
  };

  /**
   * Handles the delete process of a chat session.
   */
  const handleDeleteChat = async () => {
    if (sessionIdToDelete === null) {
      console.error("No current selected to delete");
      return;
    }

    await deleteChatSession(sessionIdToDelete);
    const updatedSessions = sessions.filter((s) => s.id !== sessionIdToDelete);
    setSessions(updatedSessions);
    setIsPopupOpen(false);
    if (updatedSessions.length === 0) {
      setCurrentSessionId(null);
    } else {
      setCurrentSessionId(updatedSessions[0].id);
    }
  };

  /**
   * Handles the creation process of a chat session.
   */
  const handleNewChat = async () => {
    const id = await createChatSession();

    if (id === "") {
      console.error("Add error showage for a couple of seconds.");
      return;
    }
    const newSession: ChatSession = {
      id,
      messages: [],
      createdAt: new Date().toISOString(),
      isLoading: false,
    };
    setSessions((prev) => [newSession, ...prev]);
    setCurrentSessionId(id);
  };

  const appendMessageToCurrentSession = (message: Message) => {
    setSessions((prevSessions) =>
      prevSessions.map((session) =>
        session.id === currentSessionId
          ? { ...session, messages: [...session.messages, message] }
          : session,
      ),
    );
  };

  /**
   * Handles the send process in a chat session.
   */
  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || !currentSessionId) {
      console.error("No sessions available.");
      return;
    }
    if (!trimmed) {
      console.error("Empty message provided.");
      return;
    }
    const userMessage: Message = {
      id: uuidv4(),
      sender: "user",
      text: trimmed,
    };

    setInput("");
    setSessions((prevSessions) =>
      prevSessions.map((session) =>
        session.id === currentSessionId
          ? { ...session, isLoading: true }
          : session,
      ),
    );
    appendMessageToCurrentSession(userMessage);

    const botReply = await fetchChatbotReply(currentSessionId!, trimmed);
    setSessions((prevSessions) =>
      prevSessions.map((session) =>
        session.id === currentSessionId
          ? { ...session, isLoading: false }
          : session,
      ),
    );
    appendMessageToCurrentSession(botReply);
  };

  const getChatLoading = (): boolean => {
    const currentChat = sessions.find((chat) => chat.id === currentSessionId);

    return currentChat ? currentChat.isLoading : false;
  };

  const openSideBar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const onSwitchChat = (chatSessionId: string) => {
    openSideBar();
    setCurrentSessionId(chatSessionId);
  };

  const openConfirmDeleteChatPopup = (chatSessionId: string) => {
    setSessionIdToDelete(chatSessionId);
    setIsPopupOpen(true);
  };

  const getWelcomePage = () => {
    return (
      <div style={chatbotStyles.containerWelcomePage}>
        <div style={chatbotStyles.boxWelcomePage}>
          <h2 style={chatbotStyles.welcomePageH2}>
            {getChatbotText("welcomeMessage")}
          </h2>
          <p>{getChatbotText("welcomeDescription")}</p>
          <button
            style={chatbotStyles.welcomePageNewChatButton}
            onClick={handleNewChat}
          >
            {getChatbotText("createNewChat")}
          </button>
        </div>
      </div>
    );
  };

  const getDeletePopup = () => {
    return (
      <div style={chatbotStyles.popupContainer}>
        <h2 style={chatbotStyles.popupTitle}>{getChatbotText("popupTitle")}</h2>
        <p style={chatbotStyles.popupMessage}>
          {getChatbotText("popupMessage")}
        </p>
        <div style={chatbotStyles.popupButtonsContainer}>
          <button
            style={chatbotStyles.popupDeleteButton}
            onClick={handleDeleteChat}
          >
            {getChatbotText("popupDeleteButton")}
          </button>
          <button
            style={chatbotStyles.popupCancelButton}
            onClick={() => {
              setIsPopupOpen(false);
              setSessionIdToDelete(null);
            }}
          >
            {getChatbotText("popupCancelButton")}
          </button>
        </div>
      </div>
    );
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={chatbotStyles.toggleButton}
      >
        {getChatbotText("toggleButtonLabel")}
      </button>

      {isOpen && (
        <div
          style={{
            ...chatbotStyles.container,
            pointerEvents: isPopupOpen ? "none" : "auto",
          }}
        >
          {isSidebarOpen && (
            <Sidebar
              onClose={() => setIsSidebarOpen(false)}
              onCreateChat={handleNewChat}
              onSwitchChat={onSwitchChat}
              chatList={sessions}
              activeChatId={currentSessionId}
              openConfirmDeleteChatPopup={openConfirmDeleteChatPopup}
            />
          )}
          {isPopupOpen && getDeletePopup()}
          <Header
            currentSessionId={currentSessionId}
            openSideBar={openSideBar}
            clearMessages={openConfirmDeleteChatPopup}
          />
          {currentSessionId !== null ? (
            <>
              <Messages
                messages={getSessionMessages(currentSessionId)}
                loading={getChatLoading()}
              />
              <Input input={input} setInput={setInput} onSend={sendMessage} />
            </>
          ) : (
            getWelcomePage()
          )}
        </div>
      )}
    </>
  );
};
