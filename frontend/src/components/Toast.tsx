import { chatbotStyles } from "../styles/styles";

interface ProactiveToastProps {
  onConfirm: () => void;
  onDismiss: () => void;
}

export const ProactiveToast = ({
  onConfirm,
  onDismiss,
}: ProactiveToastProps) => {
  return (
    <div style={chatbotStyles.toastContainer}>
      <div style={chatbotStyles.toastHeader}>
        <span>🤖 Jenkins Assistant</span>
      </div>
      <div style={chatbotStyles.toastContent}>
        I detected a build failure. Would you like me to analyze the logs for
        you?
      </div>
      <div style={chatbotStyles.toastActions}>
        <button style={chatbotStyles.toastCancelButton} onClick={onDismiss}>
          No
        </button>
        <button style={chatbotStyles.toastConfirmButton} onClick={onConfirm}>
          Yes, analyze
        </button>
      </div>
    </div>
  );
};
