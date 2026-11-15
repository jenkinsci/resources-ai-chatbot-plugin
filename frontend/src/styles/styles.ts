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
    bottom: "1.5rem",
    right: "1.5rem",
    zIndex: 1000,
    borderRadius: "50%",
    width: "52px",
    height: "52px",
    backgroundColor: "#0073e6",
    color: "white",
    fontSize: "22px",
    border: "none",
    cursor: "pointer",
    boxShadow: "0 4px 14px rgba(0, 115, 230, 0.4)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  } as CSSProperties,

  container: {
    position: "fixed",
    bottom: "5rem",
    right: "1.5rem",
    width: "min(420px, calc(100vw - 2rem))",
    height: "min(590px, calc(100vh - 6.5rem))",
    maxHeight: "calc(100dvh - 6.5rem)",
    maxWidth: "calc(100vw - 2rem)",
    backgroundColor: "var(--card-background, #ffffff)",
    border: "var(--jenkins-border, 1px solid #d1d5db)",
    borderRadius: "0.75rem",
    boxShadow:
      "var(--dialog-box-shadow, 0 10px 25px -5px rgba(0, 0, 0, 0.15), 0 8px 10px -6px rgba(0, 0, 0, 0.1))",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    zIndex: 999,
  } as CSSProperties,

  containerWelcomePage: {
    flex: 1,
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    padding: "1rem",
    overflowY: "auto",
  } as CSSProperties,

  popupBackdrop: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0, 0, 0, 0.45)",
    zIndex: 98,
    borderRadius: "0.75rem",
  } as CSSProperties,

  popupContainer: {
    pointerEvents: "auto",
    position: "absolute",
    top: "50%",
    left: "50%",
    transform: "translate(-50%, -50%)",
    width: "calc(100% - 2.5rem)",
    maxWidth: "320px",
    boxSizing: "border-box",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    padding: "1.5rem 1.25rem",
    backgroundColor: "var(--card-background, #ffffff)",
    color: "var(--text-color, #1f2937)",
    border: "1px solid var(--border-color, #d1d5db)",
    boxShadow:
      "0 10px 25px -5px rgba(0, 0, 0, 0.25), 0 8px 10px -6px rgba(0, 0, 0, 0.2)",
    borderRadius: "12px",
    zIndex: 99,
  } as CSSProperties,

  popupTitle: {
    fontSize: "1.125rem",
    fontWeight: "bold",
    color: "var(--text-color, #1f2937)",
    margin: "0 0 8px 0",
    textAlign: "center",
  } as CSSProperties,

  popupMessage: {
    fontSize: "0.875rem",
    textAlign: "center",
    color: "var(--text-color, #4b5563)",
    lineHeight: "1.4",
    margin: "0 0 1.25rem 0",
  } as CSSProperties,

  popupButtonsContainer: {
    display: "flex",
    justifyContent: "center",
    gap: "0.75rem",
    width: "100%",
  } as CSSProperties,

  popupDeleteButton: {
    backgroundColor: "#dc2626",
    color: "#ffffff",
    padding: "8px 18px",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "0.875rem",
    fontWeight: "500",
    transition: "background-color 150ms ease",
  } as CSSProperties,

  popupCancelButton: {
    backgroundColor: "#4b5563",
    color: "#ffffff",
    padding: "8px 18px",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "0.875rem",
    fontWeight: "500",
    transition: "background-color 150ms ease",
  } as CSSProperties,

  boxWelcomePage: {
    width: "100%",
    boxSizing: "border-box",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "30px",
    textAlign: "center",
    color: "#888",
  } as CSSProperties,

  welcomePageIntro: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "11px",
  } as CSSProperties,

  welcomePageH2: {
    margin: 0,
    fontSize: "1.25rem",
    fontWeight: "600",
    color: "var(--text-color, #1f2937)",
  } as CSSProperties,

  welcomePageBackendMessage: {
    margin: 0,
    padding: "0.75rem 1rem",
    width: "min(28rem, calc(100% - 2rem))",
    border: "1px solid var(--border-color)",
    borderRadius: "0.5rem",
    backgroundColor: "var(--panel-background)",
    color: "var(--text-color)",
    textAlign: "center",
    lineHeight: 1.5,
  } as CSSProperties,

  welcomePageBackendDetails: {
    margin: "0.35rem 0 0",
  } as CSSProperties,

  welcomePageCommand: {
    display: "inline-block",
    padding: "0.125rem 0.375rem",
    border: "1px solid var(--border-color)",
    borderRadius: "0.25rem",
    backgroundColor: "var(--input-color)",
    fontFamily:
      "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    fontSize: "0.875em",
  } as CSSProperties,

  welcomePageRepositoryLink: {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.25rem",
    margin: 0,
    color: "var(--link-color)",
  } as CSSProperties,

  welcomePageSetupInfo: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "9px",
    width: "100%",
    margin: 0,
  } as CSSProperties,

  welcomePageNewChatButton: {
    backgroundColor: "#0073e6",
    display: "block",
    margin: 0,
    padding: "0.625rem 1.25rem",
    borderRadius: "0.5rem",
    color: "#ffffff",
    cursor: "pointer",
    border: 0,
    fontSize: "0.9375rem",
    fontWeight: 500,
    transition: "background-color 150ms ease",
  } as CSSProperties,

  // Input

  inputWrapper: {
    display: "flex",
    flexDirection: "column",
  } as CSSProperties,

  buildFailureActionBar: {
    display: "flex",
    justifyContent: "center",
    padding: "10px 12px",
    backgroundColor: "transparent",
  } as CSSProperties,

  analyzeBuildButton: {
    width: "fit-content",
    minHeight: "36px",
    padding: "8px 14px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "6px",
    border: "1px solid #b8cde5",
    borderRadius: "6px",
    backgroundColor: "#eef4fb",
    color: "#0b66d4",
    cursor: "pointer",
    fontSize: "13px",
    fontWeight: 600,
    lineHeight: 1.2,
    transition: "background-color 150ms ease, transform 120ms ease",
  } as CSSProperties,

  attachedFilesContainer: {
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
    padding: "8px 12px",
    backgroundColor: "var(--panel-background)",
    borderBottom: "1px solid var(--border-color)",
    maxHeight: "100px",
    overflowY: "auto",
  } as CSSProperties,

  attachedFileChip: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
    padding: "4px 8px",
    backgroundColor: "var(--item-background--hover)",
    color: "var(--text-color)",
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

  attachedFilePreviewIcon: {
    display: "flex",
    alignItems: "center",
    flexShrink: 0,
  } as CSSProperties,

  attachedFileSize: {
    color: "var(--text-color)",
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
    backgroundColor: "var(--panel-background, #f8f9fa)",
    borderTop: "var(--jenkins-border, 1px solid #d1d5db)",
    color: "var(--text-color, #1f2937)",
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "8px",
    boxSizing: "border-box",
  } as CSSProperties,

  attachButton: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "38px",
    height: "38px",
    minWidth: "38px",
    padding: 0,
    border: "1px solid var(--border-color, #d1d5db)",
    borderRadius: "6px",
    backgroundColor: "var(--button-background, #f3f4f6)",
    color: "var(--text-color, #4b5563)",
    fontSize: "18px",
    cursor: "pointer",
    flexShrink: 0,
    transition: "background-color 0.2s",
  } as CSSProperties,

  input: {
    flex: 1,
    minWidth: 0,
    padding: "0.625rem 0.75rem",
    borderRadius: "6px",
    backgroundColor: "var(--input-color, #ffffff)",
    border: "1px solid var(--input-border, #d1d5db)",
    color: "var(--text-color, #1f2937)",
    fontSize: "14px",
    fontFamily: "inherit",
    boxSizing: "border-box",
    scrollbarWidth: "none",
    msOverflowStyle: "none",
    minHeight: "44px",
    maxHeight: "130px",
    resize: "none",
    overflow: "auto",
    lineHeight: "1.4",
  } as CSSProperties,

  sendButton: (input: string): CSSProperties =>
    ({
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      width: "38px",
      height: "38px",
      minWidth: "38px",
      padding: "0.5rem",
      backgroundColor: input.trim()
        ? "var(--button-background, #0073e6)"
        : "#e5e7eb",
      color: input.trim() ? "#ffffff" : "#9ca3af",
      borderRadius: "0.5rem",
      border: "none",
      cursor: input.trim() ? "pointer" : "not-allowed",
      opacity: input.trim() ? 1 : 0.6,
      flexShrink: 0,
      transition: "background-color 150ms ease, opacity 150ms ease",
    }) as CSSProperties,

  //Header

  chatbotHeader: {
    alignItems: "center",
    display: "grid",
    gridTemplateColumns: "auto 1fr auto",
    gap: "8px",
    position: "relative",
    padding: "0.625rem 0.875rem",
    backgroundColor: "var(--panel-background, #f8f9fa)",
    borderBottom: "var(--jenkins-border, 1px solid #e5e7eb)",
    color: "var(--text-color, #1f2937)",
    fontWeight: "bold",
    fontSize: "14px",
    boxSizing: "border-box",
  } as CSSProperties,

  headerActions: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    justifySelf: "end",
  } as CSSProperties,

  headerLeading: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    minWidth: 0,
  } as CSSProperties,

  backendStatusDot: (isConnected: boolean): CSSProperties => ({
    width: "8px",
    height: "8px",
    borderRadius: "50%",
    backgroundColor: isConnected ? "#16a34a" : "#dc2626",
    boxShadow: "0 0 0 2px var(--panel-background)",
  }),

  backendStatusContainer: {
    position: "relative",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "20px",
    height: "20px",
    borderRadius: "50%",
    cursor: "default",
    outline: "none",
  } as CSSProperties,

  backendStatusTooltip: {
    position: "absolute",
    top: "calc(100% + 6px)",
    left: "-4px",
    zIndex: 100,
    minWidth: "max-content",
    padding: "6px 10px",
    display: "flex",
    flexDirection: "column",
    gap: "2px",
    border: "1px solid var(--border-color, #d1d5db)",
    borderRadius: "6px",
    backgroundColor: "var(--card-background, #ffffff)",
    boxShadow: "0 4px 14px rgba(15, 23, 42, 0.16)",
    color: "var(--text-color, #1f2937)",
    fontSize: "11px",
    fontWeight: "normal",
    whiteSpace: "nowrap",
  } as CSSProperties,

  providerSelector: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    minWidth: 0,
    position: "relative",
    color: "var(--text-color)",
    fontSize: "12px",
    fontWeight: 500,
    flex: "0 1 auto",
  } as CSSProperties,

  providerControl: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "8px",
    height: "36px",
    minWidth: "160px",
    maxWidth: "220px",
    padding: "0 10px",
    border: "1px solid var(--chatbot-provider-border)",
    borderRadius: "10px",
    backgroundColor: "var(--chatbot-provider-surface)",
    boxShadow: "var(--chatbot-provider-control-shadow)",
    color: "var(--text-color)",
    font: "inherit",
    cursor: "pointer",
    textAlign: "left",
    flex: "1 1 auto",
  } as CSSProperties,

  providerControlText: {
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
    alignItems: "flex-start",
    textAlign: "left",
  } as CSSProperties,

  providerControlLabel: {
    maxWidth: "204px",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    fontSize: "13px",
    fontWeight: 600,
  } as CSSProperties,

  providerControlModel: {
    display: "none",
  } as CSSProperties,

  providerMenu: {
    position: "absolute",
    top: "calc(100% + 8px)",
    left: "50%",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    width: "320px",
    maxWidth: "calc(100vw - 32px)",
    maxHeight: "min(380px, calc(100vh - 120px))",
    overflowY: "auto",
    padding: "10px",
    backgroundColor: "var(--chatbot-provider-menu-surface)",
    border: "1px solid var(--chatbot-provider-border)",
    borderRadius: "14px",
    boxShadow: "var(--chatbot-provider-menu-shadow)",
    boxSizing: "border-box",
    zIndex: 10000,
    transform: "translateX(-50%)",
  } as CSSProperties,

  providerOption: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "10px",
    width: "100%",
    minHeight: "58px",
    padding: "9px 12px",
    border: "1px solid transparent",
    borderRadius: "10px",
    backgroundColor: "transparent",
    color: "var(--text-color)",
    font: "inherit",
    textAlign: "left",
    cursor: "pointer",
    boxSizing: "border-box",
  } as CSSProperties,

  providerOptionSelected: {
    backgroundColor: "var(--chatbot-provider-selected-surface)",
    borderColor: "var(--chatbot-provider-selected-border)",
    color: "var(--text-color)",
    boxShadow: "none",
  } as CSSProperties,

  providerOptionDisabled: {
    cursor: "not-allowed",
    color: "color-mix(in srgb, var(--text-color) 76%, transparent)",
  } as CSSProperties,

  providerOptionIcon: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "32px",
    minWidth: "32px",
    height: "32px",
    border: "1px solid var(--chatbot-provider-icon-border)",
    borderRadius: "8px",
    backgroundColor: "var(--chatbot-provider-icon-surface)",
    overflow: "hidden",
  } as CSSProperties,

  providerOptionLogo: {
    display: "block",
    width: "18px",
    height: "18px",
    objectFit: "contain",
  } as CSSProperties,

  providerOptionInitial: {
    fontSize: "15px",
    fontWeight: 600,
    lineHeight: 1,
  } as CSSProperties,

  providerOptionText: {
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
    flex: 1,
    gap: "2px",
  } as CSSProperties,

  providerOptionLabel: {
    fontSize: "14px",
    fontWeight: 600,
    lineHeight: "18px",
  } as CSSProperties,

  providerOptionModel: {
    overflow: "hidden",
    color: "var(--chatbot-provider-model)",
    opacity: 0.56,
    fontSize: "11px",
    fontFamily:
      "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    lineHeight: "16px",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  } as CSSProperties,

  providerOptionStatus: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "24px",
    minWidth: "24px",
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
    padding: "0.875rem",
    overflowY: "auto",
    fontSize: "14px",
    backgroundColor: "var(--background, #ffffff)",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    boxSizing: "border-box",
  } as CSSProperties,

  messageContainer: (sender: "user" | "jenkins-bot"): CSSProperties =>
    ({
      marginBottom: "0.5rem",
      display: "flex",
      justifyContent: sender === "user" ? "flex-end" : "flex-start",
      width: "100%",
    }) as CSSProperties,

  messageBubble: (sender: "user" | "jenkins-bot"): CSSProperties =>
    ({
      display: "inline-block",
      padding: "0.75rem 1rem",
      borderTopLeftRadius: sender === "user" ? 18 : 4,
      borderTopRightRadius: sender === "user" ? 4 : 18,
      borderBottomLeftRadius: 18,
      borderBottomRightRadius: 18,
      backgroundColor:
        sender === "user"
          ? "var(--item-background--active, #0073e6)"
          : "var(--item-background--hover, #f3f4f6)",
      color: sender === "user" ? "#ffffff" : "var(--text-color, #1f2937)",
      borderRadius: "1rem",
      border:
        sender === "user"
          ? "1px solid #0060c0"
          : "var(--jenkins-border--subtle, 1px solid #e5e7eb)",
      maxWidth: "88%",
      wordWrap: "break-word",
      fontSize: "0.9375rem",
      lineHeight: "1.5",
      textAlign: "left",
      boxShadow: "0 1px 2px rgba(0, 0, 0, 0.05)",
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

  // Code block and pipeline validation styles
  codeBlockContainer: {
    margin: "8px 0",
    borderRadius: "8px",
    overflow: "hidden",
    border: "1px solid #3d3d3d",
    backgroundColor: "#1e1e1e",
    color: "#d4d4d4",
    fontFamily:
      'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
    fontSize: "0.875rem",
    maxWidth: "100%",
    width: "100%",
    boxSizing: "border-box",
  } as CSSProperties,

  codeBlockHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "6px",
    padding: "6px 12px",
    backgroundColor: "#2d2d2d",
    borderBottom: "1px solid #3d3d3d",
    fontSize: "0.75rem",
    boxSizing: "border-box",
  } as CSSProperties,

  codeBlockLanguage: {
    color: "#9cdcfe",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    fontSize: "0.7rem",
  } as CSSProperties,

  codeBlockActionGroup: {
    display: "flex",
    gap: "6px",
    alignItems: "center",
    flexWrap: "wrap",
  } as CSSProperties,

  codeBlockButton: {
    padding: "3px 8px",
    fontSize: "0.75rem",
    borderRadius: "4px",
    border: "1px solid #555",
    backgroundColor: "#3a3a3a",
    color: "#f0f0f0",
    cursor: "pointer",
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    whiteSpace: "nowrap",
  } as CSSProperties,

  codeBlockContent: {
    margin: 0,
    padding: "10px 12px",
    overflowX: "auto",
    lineHeight: "1.45",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    backgroundColor: "#1e1e1e",
    color: "#d4d4d4",
    fontFamily:
      'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
    fontSize: "0.825rem",
    maxHeight: "360px",
    overflowY: "auto",
    boxSizing: "border-box",
  } as CSSProperties,

  validationBanner: (isValid: boolean): CSSProperties => ({
    padding: "8px 12px",
    borderTop: "1px solid #3d3d3d",
    backgroundColor: isValid
      ? "rgba(46, 125, 50, 0.2)"
      : "rgba(211, 47, 47, 0.2)",
    color: isValid ? "#81c784" : "#e57373",
    fontSize: "0.8rem",
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  }),

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
    bottom: "calc(3rem + 60px + 12px)",
    right: "2rem",
    width: "320px",
    backgroundColor: "var(--card-background)",
    border: "1px solid var(--border-color)",
    borderRadius: "0.75rem",
    boxShadow: "0 3px 8px rgba(0, 0, 0, 0.12)",
    padding: "12px",
    zIndex: 1000,
    display: "flex",
    flexDirection: "column",
    gap: "10px",
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
    display: "flex",
    flexDirection: "column",
    gap: "5px",
    fontSize: "0.85rem",
    color: "#344054",
  } as CSSProperties,

  toastFailureText: {
    color: "#a4262c",
    fontSize: "0.9rem",
    fontWeight: 700,
  } as CSSProperties,

  toastActions: {
    display: "flex",
    justifyContent: "flex-end",
    alignItems: "center",
    gap: "8px",
  } as CSSProperties,

  toastConfirmButton: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "6px",
    minHeight: "36px",
    padding: "8px 14px",
    backgroundColor: "#0b66d4",
    color: "#ffffff",
    border: "1px solid #0958b6",
    borderRadius: "6px",
    fontSize: "13px",
    fontWeight: 600,
    cursor: "pointer",
  } as CSSProperties,

  toastCancelButton: {
    backgroundColor: "transparent",
    color: "#667085",
    border: "none",
    borderRadius: "6px",
    padding: "8px 10px",
    fontSize: "13px",
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
