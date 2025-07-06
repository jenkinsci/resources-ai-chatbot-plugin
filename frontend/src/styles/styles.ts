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
    backgroundColor: "white",
    border: "1px solid #ccc",
    borderRadius: "10px",
    display: "flex",
    flexDirection: "column",
    zIndex: 999,
    boxShadow: "0 0 20px rgba(0,0,0,0.2)",
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
    backgroundColor: "rgba(44, 41, 41, 1)",
    boxShadow: "4px 4px 10px rgba(0, 0, 0, 0.4)",
    borderRadius: "10px",
    zIndex: 11,
  } as CSSProperties,

  popupTitle: {
    fontSize: "1.25rem",
    fontWeight: "bold",
    color: "#ffffff",
    marginBottom: "10px",
  } as CSSProperties,

  popupMessage: {
    fontSize: "1rem",
    textAlign: "center",
    color: "#d1d5db",
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

  inputContainer: {
    padding: "0.75rem",
    borderTop: "1px solid #eee",
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
  } as CSSProperties,

  input: {
    width: "85%",
    padding: "0.5rem",
    borderRadius: "6px",
    border: "1px solid #ccc",
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
      backgroundColor: "#0073e6",
      color: "#fff",
      border: "none",
      borderRadius: "6px",
      cursor: input.trim() ? "pointer" : "not-allowed",
      opacity: input.trim() ? 1 : 0.5,
    }) as CSSProperties,

  //Header

  chatbotHeader: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    padding: "1rem",
    borderBottom: "1px solid #eee",
    fontWeight: "bold",
    fontSize: "16px",
    backgroundColor: "#f5f5f5",
  } as CSSProperties,

  clearButton: {
    backgroundColor: "transparent",
    border: "none",
    color: "black",
    cursor: "pointer",
    fontSize: "14px",
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
      backgroundColor: sender === "user" ? "#0073e6" : "#5e5b5b",
      color: sender === "user" ? "#fff" : "#f0f0f0",
      maxWidth: "80%",
      wordWrap: "break-word",
      fontSize: "1rem",
    }) as CSSProperties,

  // Sidebar

  sidebarContainer: {
    position: "absolute",
    top: 0,
    left: 0,
    height: "96%",
    width: "250px",
    backgroundColor: "rgba(240, 240, 240, 0.9)",
    boxShadow: "2px 0 5px rgba(0,0,0,0.1)",
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
      backgroundColor: isActive ? "#d0e7ff" : "#fff",
      borderLeft: isActive ? "4px solid #0073e6" : "4px solid transparent",
      fontWeight: isActive ? "bold" : "normal",
      color: isActive ? "#0073e6" : "#333",
      cursor: "pointer",
      transition: "background 0.2s, border-left 0.2s",
    }) as CSSProperties,
};
