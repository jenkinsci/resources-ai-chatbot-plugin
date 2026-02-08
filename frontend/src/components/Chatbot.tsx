import { useState, useEffect, useRef } from "react";

import { type Message } from "../model/Message";
import { type ChatSession } from "../model/ChatSession";
import {
  fetchChatbotReply,
  fetchChatbotReplyWithFiles,
  createChatSession,
  deleteChatSession,
  fetchSupportedExtensions,
  validateFile,
  fileToAttachment,
  type SupportedExtensions,
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
import { ProactiveToast } from "./Toast";
import { useContextObserver } from "../utils/useContextObserver";

/**
 * Chatbot is the core component responsible for managing the chatbot display.
 */

const LOG_PATTERN =
  /(Started by user|Running as SYSTEM|Building in workspace|FATAL:|ERROR:|Exception:|Stack trace|Build step .*? marked build as failure)/i;

export const Chatbot = () => {
  const abortControllerRef = useRef<AbortController | null>(null);

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
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [supportedExtensions, setSupportedExtensions] =
    useState<SupportedExtensions | null>(null);

  const { showToast, setShowToast } = useContextObserver(isOpen);

  /**
   * Fetch supported file extensions on component mount.
   */
  useEffect(() => {
    const loadSupportedExtensions = async () => {
      const extensions = await fetchSupportedExtensions();
      if (extensions) {
        setSupportedExtensions(extensions);
      }
    };
    loadSupportedExtensions();
  }, []);

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
    if (sessionId === null) {
      return [];
    }
    const chatSession = sessions.find((item) => item.id === sessionId);

    if (chatSession) {
      return chatSession.messages;
    }

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
      loadingStatus: null,
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
    const hasFiles = attachedFiles.length > 0;

    if (!currentSessionId) return;
    if (!trimmed && !hasFiles) return;

    const fileAttachments = attachedFiles.map(fileToAttachment);

    const userMessage: Message = {
      id: uuidv4(),
      sender: "user",
      text: trimmed || (hasFiles ? "📎 Attached file(s)" : ""),
      files: fileAttachments.length > 0 ? fileAttachments : undefined,
    };

    setInput("");
    const filesToSend = [...attachedFiles];
    setAttachedFiles([]);
    const isLogAnalysis = LOG_PATTERN.test(trimmed);
    const statusMessage = isLogAnalysis
      ? getChatbotText("analyzingLogs")
      : getChatbotText("generatingMessage");

    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentSessionId
          ? { ...s, isLoading: true, loadingStatus: statusMessage }
          : s,
      ),
    );
    const controller = new AbortController();
    abortControllerRef.current = controller;

    appendMessageToCurrentSession(userMessage);

    try {
      const botReply =
        filesToSend.length > 0
          ? await fetchChatbotReplyWithFiles(
              currentSessionId,
              trimmed || "Please analyze the attached file(s).",
              filesToSend,
              controller.signal,
            )
          : controller.signal
            ? await fetchChatbotReply(
                currentSessionId,
                trimmed,
                controller.signal,
              )
            : await fetchChatbotReply(currentSessionId, trimmed);
      appendMessageToCurrentSession(botReply);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        // Request was intentionally cancelled
        return;
      }
      throw error;
    } finally {
      abortControllerRef.current = null;
      setSessions((prev) =>
        prev.map((s) =>
          s.id === currentSessionId
            ? { ...s, isLoading: false, loadingStatus: null }
            : s,
        ),
      );
    }
  };
  const handleCancelMessage = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;

    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentSessionId
          ? { ...s, isLoading: false, loadingStatus: null }
          : s,
      ),
    );
  };

  /**
   * Handles attaching files to the current message.
   */
  const handleFilesAttached = (files: File[]) => {
    setAttachedFiles(files);
  };

  /**
   * Handles removing a file from attachments.
   */
  const handleFileRemoved = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  /**
   * Validates a file for upload.
   */
  const handleValidateFile = (file: File) => {
    return validateFile(file, supportedExtensions);
  };

  const getChatLoading = (): boolean => {
    const currentChat = sessions.find((chat) => chat.id === currentSessionId);
    return currentChat ? currentChat.isLoading : false;
  };

  const getChatLoadingStatus = (): string | null => {
    const currentChat = sessions.find((chat) => chat.id === currentSessionId);
    return currentChat ? currentChat.loadingStatus : null;
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

  const getConsoleLogContext = (): string => {
    // 1. Try standard Jenkins console selector
    const consoleElement = document.querySelector("pre.console-output");

    if (!consoleElement || !consoleElement.textContent) {
      return "";
    }

    const fullLog = consoleElement.textContent;

    // 2. Truncate if too large (e.g., last 5000 characters)
    // We only need the error at the end, and we don't want to overload the LLM.
    const maxLength = 5000;
    if (fullLog.length > maxLength) {
      return "...(logs truncated due to size)...\n" + fullLog.slice(-maxLength);
    }

    return fullLog;
  };

  /**
   * Handlers for Proactive Toast
   */
  const handleToastConfirm = () => {
    setShowToast(false);
    setIsOpen(true);

    // 1. Scrape the logs
    const logs = getConsoleLogContext();

    // 2. Construct the prompt
    if (logs) {
      const messageWithContext = `I found a build failure. Here are the last 5000 characters of the log:\n\n\`\`\`\n${logs}\n\`\`\`\n\nCan you analyze this error?`;
      setInput(messageWithContext);

      // Optional: If you want to send it immediately without clicking the arrow button:
      // sendMessage(messageWithContext);
    } else {
      setInput(
        "I noticed a build failure, but I couldn't read the logs automatically. Can you paste them?",
      );
    }
  };

  const handleToastDismiss = () => {
    setShowToast(false);
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
      {showToast && !isOpen && (
        <ProactiveToast
          onConfirm={handleToastConfirm}
          onDismiss={handleToastDismiss}
        />
      )}

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
            messages={getSessionMessages(currentSessionId)}
          />
          {currentSessionId !== null ? (
            <>
              <Messages
                messages={getSessionMessages(currentSessionId)}
                isLoading={getChatLoading()}
                loadingStatus={getChatLoadingStatus()}
              />
              <Input
                input={input}
                setInput={setInput}
                onSend={sendMessage}
                onCancel={handleCancelMessage}
                isLoading={getChatLoading()}
                attachedFiles={attachedFiles}
                onFilesAttached={handleFilesAttached}
                onFileRemoved={handleFileRemoved}
                enableFileUpload={true}
                validateFile={handleValidateFile}
              />
            </>
          ) : (
            getWelcomePage()
          )}
        </div>
      )}
    </>
  );
};
