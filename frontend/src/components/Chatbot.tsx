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
import { Input } from "./Input";
import { getChatbotText } from "../data/chatbotTexts";
import {
  loadChatbotSessions,
  loadChatbotLastSessionId,
} from "../utils/chatbotStorage";
import { v4 as uuidv4 } from "uuid";
import { SessionNotFoundError } from "../utils/callChatbotApi";
import { ProactiveToast } from "./Toast";
import { useContextObserver } from "../utils/useContextObserver";

const LOG_PATTERN =
  /(Started by user|Running as SYSTEM|Building in workspace|FATAL:|ERROR:|Exception:|Stack trace|Build step .*? marked build as failure)/i;

export interface ChatbotProps {
  onClose?: () => void;
}

export const Chatbot = ({ onClose }: ChatbotProps) => {
  const abortControllerRef = useRef<AbortController | null>(null);

  const [isOpen, setIsOpen] = useState(true);
  const [input, setInput] = useState("");
  const [sessions, setSessions] = useState<ChatSession[]>(loadChatbotSessions);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(
    loadChatbotLastSessionId
  );
  const [sessionIdToDelete, setSessionIdToDelete] = useState<string | null>(null);
  const [isPopupOpen, setIsPopupOpen] = useState<boolean>(false);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [supportedExtensions, setSupportedExtensions] =
    useState<SupportedExtensions | null>(null);
  const [isDark, setIsDark] = useState<boolean>(false);

  const { showToast, setShowToast } = useContextObserver(isOpen);

  // Load supported extensions once
  useEffect(() => {
    const loadSupportedExtensions = async () => {
      const extensions = await fetchSupportedExtensions();
      if (extensions) {
        setSupportedExtensions(extensions);
      }
    };
    loadSupportedExtensions();
  }, []);

  // Persist sessions on unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      sessionStorage.setItem("chatbot-sessions", JSON.stringify(sessions));
      sessionStorage.setItem(
        "chatbot-last-session-id",
        currentSessionId || ""
      );
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [sessions, currentSessionId]);

  // Dark mode class toggle on <html> element
  useEffect(() => {
    const html = document.documentElement;
    if (isDark) {
      html.classList.add("dark");
    } else {
      html.classList.remove("dark");
    }
  }, [isDark]);

  const getSessionMessages = (sessionId: string | null) => {
    if (!sessionId) return [];
    const chatSession = sessions.find((item) => item.id === sessionId);
    return chatSession ? chatSession.messages : [];
  };

  const handleDeleteChat = async () => {
    if (!sessionIdToDelete) return;
    await deleteChatSession(sessionIdToDelete);
    const updated = sessions.filter((s) => s.id !== sessionIdToDelete);
    setSessions(updated);
    setIsPopupOpen(false);
    if (updated.length === 0) {
      setCurrentSessionId(null);
    } else {
      setCurrentSessionId(updated[0].id);
    }
  };

  const handleNewChat = async () => {
    let id = await createChatSession();
    if (id === "") {
      console.warn("Backend unavailable — creating local session as fallback.");
      id = uuidv4();
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
    setSessions((prev) =>
      prev.map((session) =>
        session.id === currentSessionId
          ? { ...session, messages: [...session.messages, message] }
          : session
      )
    );
  };

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
    setAttachedFiles([]);
    const isLogAnalysis = LOG_PATTERN.test(trimmed);
    const statusMessage = isLogAnalysis
      ? getChatbotText("analyzingLogs")
      : getChatbotText("generatingMessage");

    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentSessionId
          ? { ...s, isLoading: true, loadingStatus: statusMessage }
          : s
      )
    );

    const controller = new AbortController();
    abortControllerRef.current = controller;

    appendMessageToCurrentSession(userMessage);
    try {
      const botReply =
        fileAttachments.length > 0
          ? await fetchChatbotReplyWithFiles(
              currentSessionId,
              trimmed || "Please analyze the attached file(s).",
              attachedFiles,
              controller.signal
            )
          : await fetchChatbotReply(
              currentSessionId,
              trimmed,
              controller.signal
            );
      appendMessageToCurrentSession(botReply);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      if (error instanceof SessionNotFoundError) {
        console.warn(
          `Session "${currentSessionId}" not found on backend. Creating new session and retrying...`,
        );
        // Attempt to create a new session and replace the current one
        const newSessionId = await createChatSession();
        if (newSessionId) {
          setSessions((prev) =>
            prev.map((s) =>
              s.id === currentSessionId
                ? { ...s, id: newSessionId }
                : s
            )
          );
          setCurrentSessionId(newSessionId);
          // Retry sending the same message with the new session
          const retryReply = await fetchChatbotReply(
            newSessionId,
            trimmed,
            controller.signal,
          );
          appendMessageToCurrentSession(retryReply);
          return;
        }
      }
      throw error;
    } finally {
      abortControllerRef.current = null;
      setSessions((prev) =>
        prev.map((s) =>
          s.id === currentSessionId
            ? { ...s, isLoading: false, loadingStatus: null }
            : s
        )
      );
    }
  };

  const handleCancelMessage = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentSessionId ? { ...s, isLoading: false, loadingStatus: null } : s
      )
    );
  };

  const handleFilesAttached = (files: File[]) => setAttachedFiles(files);
  const handleFileRemoved = (index: number) =>
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  const handleValidateFile = (file: File) => validateFile(file, supportedExtensions);

  const getChatLoading = (): boolean => {
    const cur = sessions.find((c) => c.id === currentSessionId);
    return cur ? cur.isLoading : false;
  };
  const getChatLoadingStatus = (): string | null => {
    const cur = sessions.find((c) => c.id === currentSessionId);
    return cur ? cur.loadingStatus : null;
  };

  const openConfirmDeleteChatPopup = (chatSessionId: string) => {
    setSessionIdToDelete(chatSessionId);
    setIsPopupOpen(true);
  };

  const handleToastConfirm = () => {
    setShowToast(false);
    setIsOpen(true);
    setInput(getChatbotText("welcomeMessage"));
  };
  const handleToastDismiss = () => setShowToast(false);

  const handleClose = onClose || (() => setIsOpen(false));

  const getWelcomePage = () => (
    <div className="welcome-screen-container">
      <div className="welcome-avatar-wrapper">
        <img
          alt="Jenkins Logo"
          className="welcome-logo"
          src="https://lh3.googleusercontent.com/aida-public/AB6AXuBD-X7_6zh-ve42nEMOBvzUZNAGW5qZCOPJoNux3Sox9zhpFT0_yvHAvb0fevBzZVypWMKePiD14uHvXtDbp4nK8a-_v6Wa2zgzbj5iHLjH4TgihzAZXVpx8oYgRJlEBhd21CBwOVCqsE1SLQL-9JDU4ou12kT2yZ_g09-4aHn34jOJRIwGcCh4VuMrLwAvPbPjE3mNTSM2CO9uZa-MJCho1OSmjOr6rG6LEHjl8CJ_sJHOHXNDIDQx0BEoY1GcxcWYNC0IuTk2bn1G"
        />
      </div>
      <h2 className="welcome-title">{getChatbotText("welcomeMessage")}</h2>
      <p className="welcome-desc">{getChatbotText("welcomeDescription")}</p>
      <button className="welcome-btn" onClick={handleNewChat}>
        {getChatbotText("createNewChat")}
      </button>
    </div>
  );

  const getDeletePopup = () => (
    <div className="delete-popup-overlay">
      <div className="delete-popup-container">
        <h2 className="delete-popup-title">{getChatbotText("popupTitle")}</h2>
        <p className="delete-popup-message">{getChatbotText("popupMessage")}</p>
        <div className="delete-popup-actions">
          <button
            className="toast-btn toast-btn-confirm"
            style={{ backgroundColor: "#ef4444" }}
            onClick={handleDeleteChat}
          >
            {getChatbotText("popupDeleteButton")}
          </button>
          <button
            className="toast-btn toast-btn-cancel"
            onClick={() => {
              setIsPopupOpen(false);
              setSessionIdToDelete(null);
            }}
          >
            {getChatbotText("popupCancelButton")}
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {showToast && !isOpen && (
        <ProactiveToast onConfirm={handleToastConfirm} onDismiss={handleToastDismiss} />
      )}
      {isOpen && (
        <div className="chatbot-container">
          <Header
            currentSessionId={currentSessionId}
            clearMessages={openConfirmDeleteChatPopup}
            messages={getSessionMessages(currentSessionId)}
            isDark={isDark}
            setIsDark={setIsDark}
            onClose={handleClose}
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
          {isPopupOpen && getDeletePopup()}
        </div>
      )}
    </>
  );
};
