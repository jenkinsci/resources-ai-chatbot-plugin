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
    bottom: "3rem",
    right: "2rem",
    zIndex: 1000,
    borderRadius: "50%",
    width: "60px",
    height: "60px",
    backgroundColor: "#0073e6",
    color: "white",
    fontSize: "24px",
    border: "none",
    cursor: "pointer",
  } as CSSProperties,

  container: {
    position: "fixed",
    bottom: "6rem",
    right: "2rem",
    width: "600px",
    height: "800px",
    backgroundColor: "var(--card-background)",
    border: "var(--jenkins-border)",
    borderRadius: "0.75rem",
    boxShadow: "var(--dialog-box-shadow)",
    display: "flex",
    flexDirection: "column",
    zIndex: 999,
  } as CSSProperties,

  containerWelcomePage: {
    height: "70%",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
  } as CSSProperties,

  popupContainer: {
    pointerEvents: "auto",
    position: "absolute",
    top: 200,
    left: 100,
    height: "125px",
    width: "400px",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    padding: "2rem 1rem",
    backgroundColor: "var(--background)",
    color: "var(--text-color)",
    border: "1px solid var(--border-color)",
    boxShadow: "4px 4px 10px rgba(0, 0, 0, 0.4)",
    borderRadius: "10px",
    zIndex: 11,
  } as CSSProperties,

  popupTitle: {
    fontSize: "1.25rem",
    fontWeight: "bold",
    backgroundColor: "var(--background)",
    color: "var(--text-color)",
    border: "1px solid var(--border-color)",
    marginBottom: "10px",
  } as CSSProperties,

  popupMessage: {
    fontSize: "1rem",
    textAlign: "center",
    backgroundColor: "var(--background)",
    color: "var(--text-color)",
    border: "1px solid var(--border-color)",
    marginBottom: "1.5rem",
  } as CSSProperties,

  popupButtonsContainer: {
    display: "flex",
    justifyContent: "flex-end",
    gap: "1rem",
  } as CSSProperties,

  popupDeleteButton: {
    backgroundColor: "#dc2626",
    color: "#ffffff",
    padding: "8px 16px",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "1rem",
  } as CSSProperties,

  popupCancelButton: {
    backgroundColor: "#5e5b5b",
    color: "#ffffff",
    padding: "8px 16px",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "1rem",
  } as CSSProperties,

  boxWelcomePage: {
    textAlign: "center",
    color: "#888",
  } as CSSProperties,

  welcomePageH2: {
    marginBottom: "0.5rem",
  } as CSSProperties,

  welcomePageNewChatButton: {
    backgroundColor: "#0073e6",
    padding: "1rem",
    borderRadius: "1rem",
    color: "#ffffff",
    cursor: "pointer",
    border: 0,
  } as CSSProperties,

  // Input

  inputWrapper: {
    display: "flex",
    flexDirection: "column",
    borderTop: "1px solid #eee",
  } as CSSProperties,

  attachedFilesContainer: {
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
    padding: "8px 12px",
    backgroundColor: "#f8f9fa",
    borderBottom: "1px solid #eee",
    maxHeight: "100px",
    overflowY: "auto",
  } as CSSProperties,

  attachedFileChip: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
    padding: "4px 8px",
    backgroundColor: "#e9ecef",
    borderRadius: "16px",
    fontSize: "12px",
    maxWidth: "200px",
  } as CSSProperties,

  attachedFileName: {
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    maxWidth: "120px",
  } as CSSProperties,

  attachedFileSize: {
    color: "#6c757d",
    fontSize: "11px",
    flexShrink: 0,
  } as CSSProperties,

  removeFileButton: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "18px",
    height: "18px",
    padding: 0,
    border: "none",
    borderRadius: "50%",
    backgroundColor: "#dc3545",
    color: "#fff",
    fontSize: "14px",
    cursor: "pointer",
    flexShrink: 0,
    lineHeight: 1,
  } as CSSProperties,

  inputContainer: {
    padding: "0.75rem",
    backgroundColor: "var(--panel-background)",
    borderTop: "var(--jenkins-border)",
    border: "1px solid var(--border-color)",
    color: "var(--text-color)",

    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    gap: "8px",
  } as CSSProperties,

  attachButton: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "40px",
    height: "40px",
    padding: 0,
    border: "1px solid #ccc",
    borderRadius: "6px",
    backgroundColor: "#fff",
    fontSize: "18px",
    cursor: "pointer",
    flexShrink: 0,
    transition: "background-color 0.2s",
  } as CSSProperties,

  input: {
    width: "85%",
    padding: "0.5rem",
    borderRadius: "6px",
    borderTop: "1px solid var(--border-color)",
    backgroundColor: "var(--input-color)",
    border: "1px solid var(--input-border)",
    color: "var(--text-color)",

    fontSize: "14px",
    fontFamily: "inherit",
    boxSizing: "border-box",
    scrollbarWidth: "none",
    msOverflowStyle: "none",
    minHeight: "60px",
    maxHeight: "150px",
    resize: "none",
    overflow: "auto",
    lineHeight: "1.5",
  } as CSSProperties,

  sendButton: (input: string): CSSProperties =>
    ({
      width: "14%",
      padding: "0.5rem 1rem",
      backgroundColor: "var(--button-background)",
      color: "var(--text-color)",
      borderRadius: "0.625rem",
      border: "none",
      cursor: input.trim() ? "pointer" : "not-allowed",
      opacity: input.trim() ? 1 : 0.5,
    }) as CSSProperties,

  //Header

  chatbotHeader: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    flexDirection: "row",
    justifyContent: "space-between",
    padding: "1rem",
    backgroundColor: "var(--panel-background)",
    borderBottom: "var(--jenkins-border)",
    color: "var(--text-color)",
    fontWeight: "bold",
    fontSize: "16px",
  } as CSSProperties,

  headerActions: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  } as CSSProperties,

  clearButton: {
    backgroundColor: "transparent",
    border: "none",
    color: "inherit",
    cursor: "pointer",
    fontSize: "14px",
  } as CSSProperties,

  exportButton: {
    backgroundColor: "transparent",
    border: "none",
    color: "inherit",
    cursor: "pointer",
    fontSize: "14px",
    display: "flex",
    alignItems: "center",
    gap: "6px",
    position: "relative",
  } as CSSProperties,

  exportMenu: {
    width: "160px",
    position: "absolute",
    top: "100%",
    right: 0,
    marginTop: "8px",
    padding: "8px",

    display: "grid",
    gridTemplateColumns: "repeat(2, 1fr)",
    gap: "8px",

    backgroundColor: "var(--card-background)",
    border: "var(--jenkins-border)",
    boxShadow: "var(--dropdown-box-shadow)",
    borderRadius: "8px",
    zIndex: 10000,
  } as CSSProperties,

  exportMenuItem: {
    width: "100%",
    height: "64px",
    backgroundColor: "var(--button-background)",
    color: "var(--text-color)",
    border: "1px solid var(--border-color)",
    borderRadius: "6px",
    padding: "8px",
    cursor: "pointer",

    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "6px",
  } as CSSProperties,

  exportMenuItemHover: {
    backgroundColor: "#f0f0f0",
  } as CSSProperties,

  openSidebarButton: {
    background: "transparent",
    border: "none",
    fontSize: "1.5rem",
    cursor: "pointer",
  } as CSSProperties,

  // Messages

  messagesMain: {
    flex: 1,
    padding: "0.75rem",
    overflowY: "auto",
    fontSize: "14px",
  } as CSSProperties,

  messageContainer: (sender: "user" | "jenkins-bot"): CSSProperties =>
    ({
      marginBottom: "0.5rem",
      textAlign: sender === "user" ? "right" : "left",
    }) as CSSProperties,

  messageBubble: (sender: "user" | "jenkins-bot"): CSSProperties =>
    ({
      display: "inline-block",
      padding: "0.75rem 1rem",
      borderTopLeftRadius: sender === "user" ? 20 : 6,
      borderTopRightRadius: 20,
      borderBottomLeftRadius: 20,
      borderBottomRightRadius: sender === "user" ? 6 : 20,
      backgroundColor:
        sender === "user"
          ? "var(--item-background--active)"
          : "var(--item-background--hover)",
      color: "var(--text-color)",
      borderRadius: "0.75rem",
      border: "var(--jenkins-border--subtle)",
      maxWidth: "80%",
      wordWrap: "break-word",
      fontSize: "1rem",
    }) as CSSProperties,

  // File attachments in messages
  messageFilesContainer: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    marginBottom: "8px",
  } as CSSProperties,

  fileAttachmentContainer: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px",
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    borderRadius: "8px",
    maxWidth: "100%",
  } as CSSProperties,

  imagePreview: {
    maxWidth: "200px",
    maxHeight: "150px",
    borderRadius: "4px",
    objectFit: "contain" as const,
  } as CSSProperties,

  textFileIcon: {
    fontSize: "24px",
    flexShrink: 0,
  } as CSSProperties,

  fileAttachmentInfo: {
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  } as CSSProperties,

  fileAttachmentName: {
    fontSize: "12px",
    fontWeight: "500",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  } as CSSProperties,

  fileAttachmentSize: {
    fontSize: "10px",
    opacity: 0.8,
  } as CSSProperties,

  // Sidebar

  sidebarContainer: {
    position: "absolute",
    top: 0,
    left: 0,
    height: "96%",
    width: "250px",
    backgroundColor: "var(--background)",
    borderRight: "1px solid var(--border-color)",
    boxShadow: "var(--dropdown-shadow)",
    zIndex: 10,
    display: "flex",
    flexDirection: "column",
    padding: "1rem",
  } as CSSProperties,

  sidebarCloseButtonContainer: {
    display: "flex",
    justifyContent: "flex-end",
  } as CSSProperties,

  sidebarCloseButton: {
    background: "none",
    border: "none",
    fontSize: "1.5rem",
    cursor: "pointer",
    color: "#555",
    marginBottom: "1rem",
  } as CSSProperties,

  sidebarCreateNewChatButton: {
    marginBottom: "1rem",
    padding: "0.75rem",
    borderRadius: "0.5rem",
    border: "none",
    backgroundColor: "#0073e6",
    color: "#fff",
    cursor: "pointer",
    fontSize: "1rem",
    fontWeight: "500",
  } as CSSProperties,

  sidebarListChatsContainer: {
    overflowY: "auto",
    flex: 1,
  } as CSSProperties,

  sidebarNoChatsText: {
    color: "#666",
    textAlign: "center",
  } as CSSProperties,

  sidebarDeleteChatButton: {
    border: "none",
    backgroundColor: "transparent",
    cursor: "pointer",
  } as CSSProperties,

  sidebarChatContainer: (isActive: boolean): CSSProperties =>
    ({
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      maxHeight: "3vh",
      padding: "0.75rem",
      marginBottom: "0.5rem",
      borderRadius: "0.5rem",
      backgroundColor: isActive ? "var(--button-background)" : "transparent",
      color: "var(--text-color)",
      borderLeft: isActive
        ? "4px solid var(--button-background)"
        : "4px solid transparent",
      fontWeight: isActive ? "bold" : "normal",
      cursor: "pointer",
      transition: "background 0.2s, border-left 0.2s",
    }) as CSSProperties,

  // Toast Notification
  toastContainer: {
    position: "fixed",
    bottom: "7rem",
    right: "2rem",
    width: "300px",
    backgroundColor: "var(--card-background)",
    border: "1px solid var(--border-color)",
    borderRadius: "8px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
    padding: "1rem",
    zIndex: 1000,
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
    animation: "fadeIn 0.3s ease-in-out",
  } as CSSProperties,

  toastHeader: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    fontWeight: "bold",
    fontSize: "0.9rem",
    color: "var(--text-color)",
  } as CSSProperties,

  toastContent: {
    fontSize: "0.85rem",
    color: "var(--text-color-secondary)",
    marginBottom: "0.5rem",
  } as CSSProperties,

  toastActions: {
    display: "flex",
    justifyContent: "flex-end",
    gap: "0.5rem",
  } as CSSProperties,

  toastConfirmButton: {
    backgroundColor: "#0073e6",
    color: "white",
    border: "none",
    borderRadius: "4px",
    padding: "4px 12px",
    fontSize: "0.85rem",
    cursor: "pointer",
  } as CSSProperties,

  toastCancelButton: {
    backgroundColor: "transparent",
    color: "var(--text-color)",
    border: "1px solid var(--border-color)",
    borderRadius: "4px",
    padding: "4px 12px",
    fontSize: "0.85rem",
    cursor: "pointer",
  } as CSSProperties,

  // Loading State
  botMessage: {
    display: "flex",
    justifyContent: "flex-start",
    marginBottom: "0.5rem",
    paddingLeft: "0.5rem",
  } as CSSProperties,

  loadingContainer: {
    display: "flex",
    alignItems: "center",
    padding: "0.75rem 1rem",
    backgroundColor: "var(--item-background--hover)", // Matches standard bot bubble color
    borderRadius: "0.75rem",
    borderTopLeftRadius: "6px", // Matches bot message style
    border: "var(--jenkins-border--subtle)",
    color: "var(--text-color)",
    width: "fit-content",
    minHeight: "40px",
  } as CSSProperties,

  // Define explicit styles for each dot to avoid inline styling in the component
  loadingDot1: {
    width: "6px",
    height: "6px",
    backgroundColor: "var(--text-color)",
    borderRadius: "50%",
    animation: "bounce 1.4s infinite ease-in-out both",
    animationDelay: "0s",
  } as CSSProperties,

  loadingDot2: {
    width: "6px",
    height: "6px",
    backgroundColor: "var(--text-color)",
    borderRadius: "50%",
    animation: "bounce 1.4s infinite ease-in-out both",
    animationDelay: "0.2s",
  } as CSSProperties,

  loadingDot3: {
    width: "6px",
    height: "6px",
    backgroundColor: "var(--text-color)",
    borderRadius: "50%",
    animation: "bounce 1.4s infinite ease-in-out both",
    animationDelay: "0.4s",
  } as CSSProperties,

  loadingText: {
    marginLeft: "10px",
    fontStyle: "italic",
    opacity: 0.8,
  } as CSSProperties,
};
