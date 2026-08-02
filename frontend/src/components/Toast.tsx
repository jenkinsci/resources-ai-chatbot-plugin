import { chatbotStyles } from "../styles/styles";
import { Bot, Wrench } from "lucide-react";

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
        <Bot size={17} strokeWidth={2} aria-hidden="true" />
        <span>Jenkins Assistant</span>
      </div>
      <div style={chatbotStyles.toastContent}>
        <strong style={chatbotStyles.toastFailureText}>
          Build failure detected
        </strong>
        <span>Would you like Jenkins Assistant to analyze the logs?</span>
      </div>
      <div style={chatbotStyles.toastActions}>
        <button style={chatbotStyles.toastCancelButton} onClick={onDismiss}>
          Not now
        </button>
        <button style={chatbotStyles.toastConfirmButton} onClick={onConfirm}>
          <Wrench size={15} strokeWidth={2} aria-hidden="true" />
          <span>Analyze</span>
        </button>
      </div>
    </div>
  );
};
