import { useState, useEffect, useRef } from "react";

import { type Message } from "../model/Message";
import { type ChatSession } from "../model/ChatSession";
import {
  fetchChatbotReply,
  fetchChatbotReplyWithFiles,
  streamChatbotReply,
  createChatSession,
  deleteChatSession,
  fetchSupportedExtensions,
  validateFile,
  fileToAttachment,
  type SupportedExtensions,
} from "../api/chatbot";
import { isWebSocketSupported } from "../utils/websocketSupport";
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
 * Special ID for the temporary streaming message displayed while WebSocket is streaming.
 * This message is replaced with the final message when streaming completes.
 */
const STREAMING_MESSAGE_ID = "streaming-temp";

/**
 * Configuration for WebSocket connection lifecycle and error handling.
 */
const WS_CONFIG = {
  /** Maximum time to wait for WebSocket connection and streaming (milliseconds) */
  TIMEOUT_MS: 5000,
  /** Interval to check timeout (milliseconds) */
  CHECK_INTERVAL_MS: 100,
  /** Enable detailed error logging for debugging - controlled via VITE_DEBUG_LOGGING env var */
  DEBUG_LOGGING:
    import.meta.env.VITE_DEBUG_LOGGING === "true" ||
    import.meta.env.DEV === true,
} as const;

/**
 * Chatbot is the core component responsible for managing the chatbot display.
 */

export const Chatbot = () => {
  const abortControllerRef = useRef<AbortController | null>(null);
  const wsConnectionRef = useRef<WebSocket | null>(null);
  const currentSessionWsRef = useRef<string | null>(null);
  const wsTimeoutIdRef = useRef<NodeJS.Timeout | null>(null);

  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [sessions, setSessions] = useState<ChatSession[]>(loadChatbotSessions);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(
    loadChatbotLastSessionId
  );
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isPopupOpen, setIsPopupOpen] = useState<boolean>(false);
  const [sessionIdToDelete, setSessionIdToDelete] = useState<string | null>(
    null
  );
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [supportedExtensions, setSupportedExtensions] =
    useState<SupportedExtensions | null>(null);

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
   * Cleanup WebSocket connection and timeouts on component unmount.
   */
  useEffect(() => {
    return () => {
      if (WS_CONFIG.DEBUG_LOGGING) {
        console.debug(
          "Chatbot component unmounting, cleaning up WebSocket connections"
        );
      }
      // Clear any pending timeout
      if (wsTimeoutIdRef.current) {
        clearInterval(wsTimeoutIdRef.current);
        wsTimeoutIdRef.current = null;
      }
      // Close WebSocket connection
      if (wsConnectionRef.current) {
        wsConnectionRef.current.close();
        wsConnectionRef.current = null;
      }
    };
  }, []);

  /**
   * Close previous WebSocket connection when switching sessions.
   * This prevents connection leaks and ensures clean state transitions.
   */
  useEffect(() => {
    if (currentSessionId !== currentSessionWsRef.current) {
      // Close previous session's WebSocket connection
      if (wsConnectionRef.current) {
        if (WS_CONFIG.DEBUG_LOGGING) {
          console.debug(
            `Session switched from ${currentSessionWsRef.current} to ${currentSessionId}, closing previous connection`
          );
        }
        wsConnectionRef.current.close();
        wsConnectionRef.current = null;
      }
      // Clear any pending timeout
      if (wsTimeoutIdRef.current) {
        clearInterval(wsTimeoutIdRef.current);
        wsTimeoutIdRef.current = null;
      }
      currentSessionWsRef.current = currentSessionId;
    }
  }, [currentSessionId]);

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
          : session
      )
    );
  };

  /**
   * Handles the send process in a chat session.
   * Attempts to use WebSocket streaming first, with automatic fallback to HTTP.
   * Prevents rapid sending while a message is being streamed.
   */

  const sendMessage = async () => {
    const trimmed = input.trim();
    const hasFiles = attachedFiles.length > 0;

    if (!currentSessionId) return;
    if (!trimmed && !hasFiles) return;

    // Check if already streaming - prevent rapid sending
    const currentSession = sessions.find((s) => s.id === currentSessionId);
    if (currentSession?.isLoading) return;

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
        s.id === currentSessionId ? { ...s, isLoading: true } : s
      )
    );

    appendMessageToCurrentSession(userMessage);

    // File uploads always use HTTP endpoint
    if (filesToSend.length > 0) {
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const botReply = await fetchChatbotReplyWithFiles(
          currentSessionId,
          trimmed || "Please analyze the attached file(s).",
          filesToSend,
          controller.signal
        );
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
            s.id === currentSessionId ? { ...s, isLoading: false } : s
          )
        );
      }
      return;
    }

    // Try WebSocket streaming if supported, otherwise fallback to HTTP
    const streamingTokens: string[] = [];
    let streamingCompleted = false;
    let streamingError: Error | null = null;

    const onToken = (token: string) => {
      streamingTokens.push(token);
      // Update streaming message with accumulated tokens
      const streamingText = streamingTokens.join("");
      setSessions((prevSessions) =>
        prevSessions.map((session) =>
          session.id === currentSessionId
            ? {
                ...session,
                messages: session.messages.map((msg) =>
                  msg.id === STREAMING_MESSAGE_ID
                    ? { ...msg, text: streamingText }
                    : msg
                ),
              }
            : session
        )
      );
    };

    const onComplete = () => {
      streamingCompleted = true;
    };

    const onError = (error: Error) => {
      streamingError = error;
    };

    // Try WebSocket first if supported
    if (isWebSocketSupported()) {
      try {
        // Create temporary streaming message
        const streamingMessage: Message = {
          id: STREAMING_MESSAGE_ID,
          sender: "jenkins-bot",
          text: "",
        };
        appendMessageToCurrentSession(streamingMessage);

        // Set up mid-stream disconnection handler
        const setupDisconnectionHandler = (ws: WebSocket) => {
          const previousOnClose = ws.onclose;
          const previousOnError = ws.onerror;

          ws.onclose = (event) => {
            // If connection closed unexpectedly during streaming
            if (!streamingCompleted && !streamingError && !event.wasClean) {
              if (WS_CONFIG.DEBUG_LOGGING) {
                console.warn(
                  `WebSocket connection closed unexpectedly: ${event.code} ${event.reason || "Unknown reason"}`
                );
              }
              streamingError = new Error(
                `WebSocket disconnected mid-stream (code: ${event.code})`
              );
            }
            // Restore previous handler
            if (previousOnClose) previousOnClose.call(ws, event);
          };

          ws.onerror = (error) => {
            if (!streamingCompleted && !streamingError) {
              if (WS_CONFIG.DEBUG_LOGGING) {
                console.error("WebSocket error during streaming:", error);
              }
              streamingError = new Error(
                `WebSocket error: ${error instanceof Error ? error.message : "Unknown error"}`
              );
            }
            // Restore previous handler
            if (previousOnError) previousOnError.call(ws, error);
          };
        };

        // Check if we can reuse existing WebSocket connection
        const canReuseConnection =
          wsConnectionRef.current &&
          currentSessionWsRef.current === currentSessionId &&
          wsConnectionRef.current.readyState === WebSocket.OPEN;

        if (canReuseConnection) {
          // Reuse existing connection
          // We still need to set up handlers for this specific message streaming
          const ws = wsConnectionRef.current!;

          // Store current message handlers for reused connection
          const previousOnMessage = ws.onmessage;

          ws.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);

              if (data.token !== undefined) {
                // Token message: {token: "word"}
                onToken(data.token);
              } else if (data.end === true) {
                // Completion message: {end: true}
                onComplete();
                // Restore previous handler if exists, or clear it
                ws.onmessage = previousOnMessage;
              } else if (data.error) {
                // Error message: {error: "message"}
                onError(new Error(data.error));
                // Restore previous handler if exists, or clear it
                ws.onmessage = previousOnMessage;
              }
            } catch (parseError) {
              onError(
                new Error(
                  `Failed to parse WebSocket message: ${parseError instanceof Error ? parseError.message : "Unknown error"}`
                )
              );
              ws.onmessage = previousOnMessage;
            }
          };

          // Set up disconnection handlers
          setupDisconnectionHandler(ws);

          // Send message on reused connection
          if (ws.readyState === WebSocket.OPEN) {
            if (WS_CONFIG.DEBUG_LOGGING) {
              console.debug(
                `Reusing WebSocket connection for session ${currentSessionId}`
              );
            }
            ws.send(JSON.stringify({ message: trimmed }));
          } else {
            // Connection lost, create new one
            if (WS_CONFIG.DEBUG_LOGGING) {
              console.warn(
                `Connection lost (readyState: ${ws.readyState}), creating new connection`
              );
            }
            wsConnectionRef.current = streamChatbotReply(
              currentSessionId,
              trimmed,
              onToken,
              onComplete,
              onError
            );
            if (wsConnectionRef.current) {
              setupDisconnectionHandler(wsConnectionRef.current);
            }
          }
        } else {
          // Create new connection for this session
          if (WS_CONFIG.DEBUG_LOGGING) {
            console.debug(
              `Creating new WebSocket connection for session ${currentSessionId}`
            );
          }
          wsConnectionRef.current = streamChatbotReply(
            currentSessionId,
            trimmed,
            onToken,
            onComplete,
            onError
          );
          currentSessionWsRef.current = currentSessionId;

          // Set up disconnection handlers
          if (wsConnectionRef.current) {
            setupDisconnectionHandler(wsConnectionRef.current);
          }
        }

        // Enhanced timeout handling with cleanup
        let timeout = 0;
        const timeoutInterval = setInterval(() => {
          timeout += WS_CONFIG.CHECK_INTERVAL_MS;

          // Check for mid-stream disconnection
          if (
            wsConnectionRef.current &&
            wsConnectionRef.current.readyState === WebSocket.CLOSED &&
            !streamingCompleted
          ) {
            if (WS_CONFIG.DEBUG_LOGGING) {
              console.warn(
                "WebSocket disconnected, triggering fallback to HTTP"
              );
            }
            clearInterval(timeoutInterval);
            if (!streamingError) {
              streamingError = new Error(
                "WebSocket disconnected mid-stream, falling back to HTTP"
              );
            }
            return;
          }

          // Timeout after configured duration
          if (timeout > WS_CONFIG.TIMEOUT_MS) {
            clearInterval(timeoutInterval);
            if (!streamingCompleted && !streamingError) {
              if (WS_CONFIG.DEBUG_LOGGING) {
                console.warn(
                  `WebSocket connection timeout (${WS_CONFIG.TIMEOUT_MS}ms), falling back to HTTP`
                );
              }
              streamingError = new Error(
                `WebSocket connection timeout after ${WS_CONFIG.TIMEOUT_MS}ms, falling back to HTTP`
              );
              if (wsConnectionRef.current) {
                wsConnectionRef.current.close();
                wsConnectionRef.current = null;
              }
            }
          }
        }, WS_CONFIG.CHECK_INTERVAL_MS);

        // Store timeout ID for cleanup
        wsTimeoutIdRef.current = timeoutInterval;

        // Wait for streaming or error
        while (
          !streamingCompleted &&
          !streamingError &&
          timeout <= WS_CONFIG.TIMEOUT_MS
        ) {
          await new Promise((resolve) =>
            setTimeout(resolve, WS_CONFIG.CHECK_INTERVAL_MS)
          );
        }

        clearInterval(timeoutInterval);
        wsTimeoutIdRef.current = null;

        if (streamingError) {
          // Remove streaming message and fallback to HTTP
          setSessions((prevSessions) =>
            prevSessions.map((session) =>
              session.id === currentSessionId
                ? {
                    ...session,
                    messages: session.messages.filter(
                      (msg) => msg.id !== STREAMING_MESSAGE_ID
                    ),
                  }
                : session
            )
          );

          // Fallback to HTTP
          if (WS_CONFIG.DEBUG_LOGGING) {
            const errorMsg = streamingError
              ? (streamingError as Error).message || String(streamingError)
              : "Unknown error";
            console.warn(
              `WebSocket streaming failed: ${errorMsg}\nFalling back to HTTP for session ${currentSessionId}`,
              streamingError
            );
          }
          const controller = new AbortController();
          abortControllerRef.current = controller;

          try {
            if (WS_CONFIG.DEBUG_LOGGING) {
              console.debug(
                `Attempting HTTP fallback for session ${currentSessionId}`
              );
            }
            const botReply = await fetchChatbotReply(
              currentSessionId,
              trimmed,
              controller.signal
            );
            appendMessageToCurrentSession(botReply);
            if (WS_CONFIG.DEBUG_LOGGING) {
              console.debug(
                `HTTP fallback successful for session ${currentSessionId}`
              );
            }
          } catch (error) {
            if (error instanceof DOMException && error.name === "AbortError") {
              if (WS_CONFIG.DEBUG_LOGGING) {
                console.debug(
                  `HTTP request cancelled for session ${currentSessionId}`
                );
              }
              return;
            }
            if (WS_CONFIG.DEBUG_LOGGING) {
              console.error(
                `HTTP fallback also failed for session ${currentSessionId}:`,
                error
              );
            }
            throw error;
          } finally {
            abortControllerRef.current = null;
          }
        } else if (streamingCompleted) {
          // Replace streaming message with final message
          const finalMessage: Message = {
            id: uuidv4(),
            sender: "jenkins-bot",
            text: streamingTokens.join(""),
          };

          if (WS_CONFIG.DEBUG_LOGGING) {
            console.debug(
              `WebSocket streaming completed successfully for session ${currentSessionId}`
            );
          }

          setSessions((prevSessions) =>
            prevSessions.map((session) =>
              session.id === currentSessionId
                ? {
                    ...session,
                    messages: session.messages.map((msg) =>
                      msg.id === STREAMING_MESSAGE_ID ? finalMessage : msg
                    ),
                  }
                : session
            )
          );
        }
      } catch (error) {
        if (WS_CONFIG.DEBUG_LOGGING) {
          console.error(
            `Unexpected error in WebSocket streaming for session ${currentSessionId}:`,
            error
          );
        }

        // Remove streaming message and fallback to HTTP
        setSessions((prevSessions) =>
          prevSessions.map((session) =>
            session.id === currentSessionId
              ? {
                  ...session,
                  messages: session.messages.filter(
                    (msg) => msg.id !== STREAMING_MESSAGE_ID
                  ),
                }
              : session
          )
        );

        // Fallback to HTTP
        const controller = new AbortController();
        abortControllerRef.current = controller;

        try {
          if (WS_CONFIG.DEBUG_LOGGING) {
            console.debug(
              `Error in WebSocket streaming, attempting HTTP fallback for session ${currentSessionId}`
            );
          }
          const botReply = await fetchChatbotReply(
            currentSessionId,
            trimmed,
            controller.signal
          );
          appendMessageToCurrentSession(botReply);
          if (WS_CONFIG.DEBUG_LOGGING) {
            console.debug(
              `HTTP fallback successful after error for session ${currentSessionId}`
            );
          }
        } catch (innerError) {
          if (
            innerError instanceof DOMException &&
            innerError.name === "AbortError"
          ) {
            if (WS_CONFIG.DEBUG_LOGGING) {
              console.debug(
                `HTTP fallback request cancelled for session ${currentSessionId}`
              );
            }
            return;
          }
          if (WS_CONFIG.DEBUG_LOGGING) {
            console.error(
              `HTTP fallback also failed after WebSocket error for session ${currentSessionId}:`,
              innerError
            );
          }
          throw innerError;
        } finally {
          abortControllerRef.current = null;
        }
      }
    } else {
      // WebSocket not supported, use HTTP directly
      if (WS_CONFIG.DEBUG_LOGGING) {
        console.debug(
          `WebSocket not supported, using HTTP for session ${currentSessionId}`
        );
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const botReply = await fetchChatbotReply(
          currentSessionId,
          trimmed,
          controller.signal
        );
        appendMessageToCurrentSession(botReply);
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          if (WS_CONFIG.DEBUG_LOGGING) {
            console.debug(
              `HTTP request cancelled for session ${currentSessionId}`
            );
          }
          return;
        }
        if (WS_CONFIG.DEBUG_LOGGING) {
          console.error(
            `HTTP request failed for session ${currentSessionId}:`,
            error
          );
        }
        throw error;
      } finally {
        abortControllerRef.current = null;
      }
    }

    // Mark loading complete
    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentSessionId ? { ...s, isLoading: false } : s
      )
    );
  };

  /**
   * Handles canceling the current message.
   * Closes WebSocket connection if streaming, or aborts HTTP request.
   */
  const handleCancelMessage = () => {
    // Close WebSocket connection if active
    if (wsConnectionRef.current) {
      wsConnectionRef.current.close();
      wsConnectionRef.current = null;
      // Remove streaming message if present
      setSessions((prevSessions) =>
        prevSessions.map((session) =>
          session.id === currentSessionId
            ? {
                ...session,
                messages: session.messages.filter(
                  (msg) => msg.id !== STREAMING_MESSAGE_ID
                ),
              }
            : session
        )
      );
    }

    // Abort HTTP request if active
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;

    setSessions((prev) =>
      prev.map((s) =>
        s.id === currentSessionId ? { ...s, isLoading: false } : s
      )
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
