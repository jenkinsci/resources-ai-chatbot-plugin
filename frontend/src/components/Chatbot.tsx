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
  analyzeBuildFailure,
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

/**
 * Chatbot is the core component responsible for managing the chatbot display.
 */

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
  const [showBuildAnalysisModal, setShowBuildAnalysisModal] = useState(false);
  const [buildUrlInput, setBuildUrlInput] = useState("");

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
   * Handles the build failure analysis.
   */
  const handleAnalyzeBuildFailure = async () => {
    if (!currentSessionId || !buildUrlInput.trim()) return;

    const buildUrl = buildUrlInput.trim();
    setBuildUrlInput("");
    setShowBuildAnalysisModal(false);

    // Add user message
    const userMessage: Message = {
      id: uuidv4(),
      sender: "user",
      text: `🔍 Analyze Build Failure: ${buildUrl}`,
    };
    appendMessageToCurrentSession(userMessage);

    // Set loading
    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentSessionId ? { ...s, isLoading: true } : s,
      ),
    );

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const botReply = await analyzeBuildFailure(
        currentSessionId,
        buildUrl,
        controller.signal,
      );
      appendMessageToCurrentSession(botReply);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      throw error;
    } finally {
      abortControllerRef.current = null;
      setSessions((prev) =>
        prev.map((s) =>
          s.id === currentSessionId ? { ...s, isLoading: false } : s,
        ),
      );
    }
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

    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentSessionId ? { ...s, isLoading: true } : s,
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
          s.id === currentSessionId ? { ...s, isLoading: false } : s,
        ),
      );
    }
  };
  const handleCancelMessage = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;

    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentSessionId ? { ...s, isLoading: false } : s,
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
            messages={getSessionMessages(currentSessionId)}
          />
          {currentSessionId !== null ? (
            <>
              {/* Build Analysis Modal */}
              {showBuildAnalysisModal && (
                <div style={{
                  position: 'fixed',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: 'rgba(0, 0, 0, 0.5)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  zIndex: 1000,
                }}>
                  <div style={{
                    background: '#1e1e1e',
                    padding: '24px',
                    borderRadius: '12px',
                    width: '400px',
                    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
                  }}>
                    <h3 style={{ margin: '0 0 16px', color: '#fff' }}>
                      🔍 Analyze Build Failure
                    </h3>
                    <p style={{ color: '#aaa', fontSize: '14px', marginBottom: '16px' }}>
                      Enter the Jenkins build URL to analyze:
                    </p>
                    <input
                      type="text"
                      value={buildUrlInput}
                      onChange={(e) => setBuildUrlInput(e.target.value)}
                      placeholder="https://ci.jenkins.io/job/.../123/"
                      style={{
                        width: '100%',
                        padding: '10px',
                        borderRadius: '6px',
                        border: '1px solid #444',
                        background: '#2a2a2a',
                        color: '#fff',
                        marginBottom: '16px',
                        boxSizing: 'border-box',
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && buildUrlInput.trim()) {
                          handleAnalyzeBuildFailure();
                        }
                      }}
                    />
                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                      <button
                        onClick={() => {
                          setShowBuildAnalysisModal(false);
                          setBuildUrlInput('');
                        }}
                        style={{
                          padding: '8px 16px',
                          borderRadius: '6px',
                          border: '1px solid #444',
                          background: 'transparent',
                          color: '#aaa',
                          cursor: 'pointer',
                        }}
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleAnalyzeBuildFailure}
                        disabled={!buildUrlInput.trim()}
                        style={{
                          padding: '8px 16px',
                          borderRadius: '6px',
                          border: 'none',
                          background: buildUrlInput.trim() ? '#4CAF50' : '#333',
                          color: buildUrlInput.trim() ? '#fff' : '#666',
                          cursor: buildUrlInput.trim() ? 'pointer' : 'not-allowed',
                        }}
                      >
                        Analyze
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Analyze Build Button */}
              <div style={{
                padding: '8px 16px',
                borderBottom: '1px solid #333',
                background: '#1a1a1a',
              }}>
                <button
                  onClick={() => setShowBuildAnalysisModal(true)}
                  disabled={getChatLoading()}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '6px',
                    border: '1px solid #4CAF50',
                    background: 'transparent',
                    color: '#4CAF50',
                    cursor: getChatLoading() ? 'not-allowed' : 'pointer',
                    fontSize: '14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    opacity: getChatLoading() ? 0.5 : 1,
                  }}
                >
                  🔍 Analyze Build Failure
                </button>
              </div>

              <Messages
                messages={getSessionMessages(currentSessionId)}
                loading={getChatLoading()}
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
