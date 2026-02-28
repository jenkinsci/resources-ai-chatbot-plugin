import { type CSSProperties } from "react";

/**
 * Styles used throughout the chatbot UI components.
 * These are organized by component responsibility
 * (e.g. Chatbot, Input, Header, Messages).
 */
export const chatbotStyles = {
  // Chatbot

  toggleButton: {
    position: "fixed",
    bottom: "2rem",
    right: "2rem",
    zIndex: 1000,
    borderRadius: "1rem",
    width: "56px",
    height: "56px",
    backgroundColor: "var(--primary-color)",
    color: "white",
    fontSize: "24px",
    border: "none",
    cursor: "pointer",
    boxShadow: "var(--shadow-lg)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "transform 0.2s ease, background-color 0.2s ease",
  } as CSSProperties,

  container: {
    position: "fixed",
    bottom: "6rem",
    right: "2rem",
    width: "420px",
    height: "680px",
    backgroundColor: "var(--card-background)",
    border: "1px solid var(--border-color)",
    borderRadius: "1.25rem",
    boxShadow: "var(--shadow-lg)",
    display: "flex",
    flexDirection: "column",
    zIndex: 999,
    overflow: "hidden",
    animation: "fadeIn 0.3s ease-out",
  } as CSSProperties,

  containerWelcomePage: {
    height: "100%",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    padding: "2rem",
  } as CSSProperties,

  popupContainer: {
    pointerEvents: "auto",
    position: "absolute",
    top: "50%",
    left: "50%",
    transform: "translate(-50%, -50%)",
    width: "85%",
    display: "flex",
    flexDirection: "column",
    padding: "1.5rem",
    backgroundColor: "var(--card-background)",
    color: "var(--text-color)",
    border: "1px solid var(--border-color)",
    boxShadow: "var(--shadow-lg)",
    borderRadius: "1rem",
    zIndex: 1001,
  } as CSSProperties,

  popupTitle: {
    fontSize: "1.125rem",
    fontWeight: "600",
    color: "var(--text-color)",
    marginBottom: "0.75rem",
    fontFamily: "Outfit, sans-serif",
  } as CSSProperties,

  popupMessage: {
    fontSize: "0.9375rem",
    color: "var(--text-secondary)",
    marginBottom: "1.5rem",
    lineHeight: "1.5",
  } as CSSProperties,

  popupButtonsContainer: {
    display: "flex",
    justifyContent: "flex-end",
    gap: "0.75rem",
  } as CSSProperties,

  popupDeleteButton: {
    backgroundColor: "#ef4444",
    color: "#ffffff",
    padding: "0.5rem 1rem",
    border: "none",
    borderRadius: "0.5rem",
    cursor: "pointer",
    fontSize: "0.875rem",
    fontWeight: "500",
  } as CSSProperties,

  popupCancelButton: {
    backgroundColor: "transparent",
    color: "var(--text-color)",
    padding: "0.5rem 1rem",
    border: "1px solid var(--border-color)",
    borderRadius: "0.5rem",
    cursor: "pointer",
    fontSize: "0.875rem",
    fontWeight: "500",
  } as CSSProperties,

  boxWelcomePage: {
    textAlign: "center",
  } as CSSProperties,

  welcomePageH2: {
    fontSize: "1.75rem",
    fontWeight: "700",
    color: "var(--text-color)",
    marginBottom: "1rem",
    fontFamily: "Outfit, sans-serif",
  } as CSSProperties,

  welcomePageNewChatButton: {
    backgroundColor: "var(--primary-color)",
    padding: "0.875rem 2rem",
    borderRadius: "0.75rem",
    color: "#ffffff",
    cursor: "pointer",
    border: "none",
    fontSize: "1rem",
    fontWeight: "600",
    boxShadow: "var(--shadow-md)",
    transition: "background-color 0.2s",
  } as CSSProperties,

  // Input

  inputWrapper: {
    display: "flex",
    flexDirection: "column",
    padding: "1rem",
    borderTop: "1px solid var(--border-color)",
    backgroundColor: "var(--card-background)",
  } as CSSProperties,

  attachedFilesContainer: {
    display: "flex",
    flexWrap: "wrap",
    gap: "0.5rem",
    paddingBottom: "0.75rem",
    maxHeight: "100px",
    overflowY: "auto",
  } as CSSProperties,

  attachedFileChip: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.375rem 0.625rem",
    backgroundColor: "var(--input-background)",
    border: "1px solid var(--border-color)",
    borderRadius: "0.5rem",
    fontSize: "0.75rem",
    maxWidth: "180px",
  } as CSSProperties,

  attachedFileName: {
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    maxWidth: "100px",
    color: "var(--text-color)",
  } as CSSProperties,

  attachedFileSize: {
    color: "var(--text-secondary)",
    fontSize: "0.6875rem",
    flexShrink: 0,
  } as CSSProperties,

  removeFileButton: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "16px",
    height: "16px",
    padding: 0,
    border: "none",
    borderRadius: "50%",
    backgroundColor: "#ef4444",
    color: "#fff",
    fontSize: "10px",
    cursor: "pointer",
    flexShrink: 0,
  } as CSSProperties,

  inputContainer: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    gap: "0.75rem",
    backgroundColor: "var(--input-background)",
    padding: "0.5rem 0.75rem",
    borderRadius: "0.75rem",
    border: "1px solid var(--border-color)",
  } as CSSProperties,

  attachButton: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "32px",
    height: "32px",
    padding: 0,
    border: "none",
    backgroundColor: "transparent",
    color: "var(--text-secondary)",
    cursor: "pointer",
    transition: "color 0.2s",
  } as CSSProperties,

  input: {
    flex: 1,
    padding: "0.5rem 0",
    border: "none",
    backgroundColor: "transparent",
    color: "var(--text-color)",
    fontSize: "0.9375rem",
    fontFamily: "inherit",
    boxSizing: "border-box",
    minHeight: "24px",
    maxHeight: "120px",
    resize: "none",
    overflow: "auto",
    lineHeight: "1.5",
    outline: "none",
  } as CSSProperties,

  sendButton: (input: string): CSSProperties =>
    ({
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      width: "32px",
      height: "32px",
      backgroundColor: input.trim() ? "var(--primary-color)" : "transparent",
      color: input.trim() ? "#ffffff" : "var(--text-secondary)",
      borderRadius: "0.5rem",
      border: "none",
      cursor: input.trim() ? "pointer" : "default",
      transition: "all 0.2s",
    }) as CSSProperties,

  //Header

  chatbotHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "1rem 1.25rem",
    backgroundColor: "var(--card-background)",
    borderBottom: "1px solid var(--border-color)",
    color: "var(--text-color)",
    zIndex: 10,
  } as CSSProperties,

  headerTitleContainer: {
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
  } as CSSProperties,

  headerTitle: {
    fontSize: "1rem",
    fontWeight: "600",
    fontFamily: "Outfit, sans-serif",
  } as CSSProperties,

  headerActions: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
  } as CSSProperties,

  clearButton: {
    backgroundColor: "transparent",
    border: "none",
    color: "var(--text-secondary)",
    cursor: "pointer",
    padding: "0.375rem",
    borderRadius: "0.375rem",
    display: "flex",
    alignItems: "center",
    transition: "background-color 0.2s",
  } as CSSProperties,

  exportButton: {
    backgroundColor: "transparent",
    border: "none",
    color: "var(--text-secondary)",
    cursor: "pointer",
    padding: "0.375rem",
    borderRadius: "0.375rem",
    display: "flex",
    alignItems: "center",
    gap: "0.375rem",
    position: "relative",
    transition: "background-color 0.2s",
  } as CSSProperties,

  exportMenu: {
    width: "180px",
    position: "absolute",
    top: "calc(100% + 0.5rem)",
    right: 0,
    backgroundColor: "var(--card-background)",
    border: "1px solid var(--border-color)",
    boxShadow: "var(--shadow-lg)",
    borderRadius: "0.75rem",
    padding: "0.5rem",
    zIndex: 10000,
    display: "flex",
    flexDirection: "column",
    gap: "0.25rem",
  } as CSSProperties,

  exportMenuItem: {
    width: "100%",
    backgroundColor: "transparent",
    color: "var(--text-color)",
    border: "none",
    borderRadius: "0.5rem",
    padding: "0.625rem 0.75rem",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "0.625rem",
    fontSize: "0.875rem",
    transition: "background-color 0.2s",
  } as CSSProperties,

  openSidebarButton: {
    background: "transparent",
    border: "none",
    color: "var(--text-secondary)",
    cursor: "pointer",
    padding: "0.375rem",
    borderRadius: "0.375rem",
    display: "flex",
    alignItems: "center",
  } as CSSProperties,

  // Messages

  messagesMain: {
    flex: 1,
    padding: "1.25rem",
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
    scrollBehavior: "smooth",
  } as CSSProperties,

  messageContainer: (sender: "user" | "jenkins-bot"): CSSProperties =>
    ({
      display: "flex",
      flexDirection: "column",
      alignItems: sender === "user" ? "flex-end" : "flex-start",
      width: "100%",
    }) as CSSProperties,

  messageBubble: (sender: "user" | "jenkins-bot"): CSSProperties =>
    ({
      display: "inline-block",
      padding: "0.75rem 1rem",
      backgroundColor:
        sender === "user" ? "var(--user-bubble)" : "var(--bot-bubble)",
      color: sender === "user" ? "var(--user-text)" : "var(--text-color)",
      borderRadius: "1rem",
      borderBottomRightRadius: sender === "user" ? "0.25rem" : "1rem",
      borderBottomLeftRadius: sender === "jenkins-bot" ? "0.25rem" : "1rem",
      maxWidth: "85%",
      wordWrap: "break-word",
      fontSize: "0.9375rem",
      lineHeight: "1.5",
      boxShadow: "var(--shadow-sm)",
    }) as CSSProperties,

  // File attachments in messages
  messageFilesContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
    marginBottom: "0.5rem",
    width: "100%",
    alignItems: "inherit",
  } as CSSProperties,

  fileAttachmentContainer: {
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
    padding: "0.625rem",
    backgroundColor: "var(--input-background)",
    borderRadius: "0.75rem",
    border: "1px solid var(--border-color)",
    maxWidth: "240px",
  } as CSSProperties,

  imagePreview: {
    maxWidth: "100%",
    maxHeight: "200px",
    borderRadius: "0.5rem",
    objectFit: "cover",
    marginTop: "0.25rem",
    border: "1px solid var(--border-color)",
  } as CSSProperties,

  textFileIcon: {
    color: "var(--primary-color)",
    flexShrink: 0,
  } as CSSProperties,

  fileAttachmentInfo: {
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  } as CSSProperties,

  fileAttachmentName: {
    fontSize: "0.8125rem",
    fontWeight: "500",
    color: "var(--text-color)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  } as CSSProperties,

  fileAttachmentSize: {
    fontSize: "0.6875rem",
    color: "var(--text-secondary)",
  } as CSSProperties,

  // Sidebar

  sidebarContainer: {
    position: "absolute",
    top: 0,
    left: 0,
    height: "100%",
    width: "280px",
    backgroundColor: "var(--card-background)",
    borderRight: "1px solid var(--border-color)",
    boxShadow: "var(--shadow-lg)",
    zIndex: 100,
    display: "flex",
    flexDirection: "column",
    animation: "slideIn 0.3s ease-out",
  } as CSSProperties,

  sidebarHeader: {
    padding: "1.25rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottom: "1px solid var(--border-color)",
  } as CSSProperties,

  sidebarTitle: {
    fontSize: "1.125rem",
    fontWeight: "600",
    fontFamily: "Outfit, sans-serif",
  } as CSSProperties,

  sidebarCloseButton: {
    background: "transparent",
    border: "none",
    color: "var(--text-secondary)",
    cursor: "pointer",
    padding: "0.375rem",
    borderRadius: "0.375rem",
    display: "flex",
    alignItems: "center",
  } as CSSProperties,

  sidebarContent: {
    flex: 1,
    padding: "1rem",
    overflowY: "auto",
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
  } as CSSProperties,

  sidebarCreateNewChatButton: {
    padding: "0.75rem",
    borderRadius: "0.75rem",
    border: "1px dashed var(--border-color)",
    backgroundColor: "var(--input-background)",
    color: "var(--text-color)",
    cursor: "pointer",
    fontSize: "0.9375rem",
    fontWeight: "500",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "0.5rem",
    marginBottom: "0.5rem",
    transition: "all 0.2s",
  } as CSSProperties,

  sidebarListChatsContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "0.25rem",
  } as CSSProperties,

  sidebarNoChatsText: {
    color: "var(--text-secondary)",
    textAlign: "center",
    padding: "2rem 0",
    fontSize: "0.875rem",
  } as CSSProperties,

  sidebarChatContainer: (isActive: boolean): CSSProperties =>
    ({
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: "0.75rem",
      borderRadius: "0.75rem",
      backgroundColor: isActive ? "var(--input-background)" : "transparent",
      color: "var(--text-color)",
      border: isActive ? "1px solid var(--border-color)" : "1px solid transparent",
      cursor: "pointer",
      transition: "all 0.2s",
    }) as CSSProperties,

  sidebarChatTitle: {
    fontSize: "0.875rem",
    fontWeight: "500",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    flex: 1,
  } as CSSProperties,

  sidebarDeleteChatButton: {
    border: "none",
    backgroundColor: "transparent",
    color: "var(--text-secondary)",
    cursor: "pointer",
    padding: "0.25rem",
    borderRadius: "0.25rem",
    display: "flex",
    alignItems: "center",
    opacity: 0,
    transition: "opacity 0.2s, color 0.2s",
  } as CSSProperties,

  // Toast Notification
  toastContainer: {
    position: "absolute",
    bottom: "1rem",
    left: "1rem",
    right: "1rem",
    backgroundColor: "var(--card-background)",
    border: "1px solid var(--border-color)",
    borderRadius: "0.75rem",
    boxShadow: "var(--shadow-lg)",
    padding: "1rem",
    zIndex: 1000,
    display: "flex",
    flexDirection: "column",
    gap: "0.75rem",
    animation: "fadeIn 0.3s ease-out",
  } as CSSProperties,

  toastHeader: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    fontWeight: "600",
    fontSize: "0.9375rem",
    color: "var(--text-color)",
  } as CSSProperties,

  toastContent: {
    fontSize: "0.875rem",
    color: "var(--text-secondary)",
    lineHeight: "1.4",
  } as CSSProperties,

  toastActions: {
    display: "flex",
    justifyContent: "flex-end",
    gap: "0.5rem",
  } as CSSProperties,

  toastConfirmButton: {
    backgroundColor: "#ef4444",
    color: "white",
    border: "none",
    borderRadius: "0.5rem",
    padding: "0.5rem 1rem",
    fontSize: "0.8125rem",
    fontWeight: "600",
    cursor: "pointer",
  } as CSSProperties,

  toastCancelButton: {
    backgroundColor: "transparent",
    color: "var(--text-color)",
    border: "1px solid var(--border-color)",
    borderRadius: "0.5rem",
    padding: "0.5rem 1rem",
    fontSize: "0.8125rem",
    fontWeight: "600",
    cursor: "pointer",
  } as CSSProperties,

  // Loading State
  botMessage: {
    display: "flex",
    justifyContent: "flex-start",
    marginBottom: "0.5rem",
  } as CSSProperties,

  loadingContainer: {
    display: "flex",
    alignItems: "center",
    padding: "0.75rem 1rem",
    backgroundColor: "var(--bot-bubble)",
    borderRadius: "1rem",
    borderBottomLeftRadius: "0.25rem",
    color: "var(--text-color)",
    width: "fit-content",
    minHeight: "40px",
    boxShadow: "var(--shadow-sm)",
  } as CSSProperties,

  loadingDot1: {
    width: "6px",
    height: "6px",
    backgroundColor: "var(--text-secondary)",
    borderRadius: "50%",
    animation: "blink 1.4s infinite ease-in-out both",
    animationDelay: "0s",
  } as CSSProperties,

  loadingDot2: {
    width: "6px",
    height: "6px",
    backgroundColor: "var(--text-secondary)",
    borderRadius: "50%",
    animation: "blink 1.4s infinite ease-in-out both",
    animationDelay: "0.2s",
  } as CSSProperties,

  loadingDot3: {
    width: "6px",
    height: "6px",
    backgroundColor: "var(--text-secondary)",
    borderRadius: "50%",
    animation: "blink 1.4s infinite ease-in-out both",
    animationDelay: "0.4s",
  } as CSSProperties,

  loadingText: {
    marginLeft: "10px",
    fontSize: "0.875rem",
    color: "var(--text-secondary)",
  } as CSSProperties,
};
