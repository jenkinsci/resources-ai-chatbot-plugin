import { chatbotStyles } from "../styles/styles";
import { AlertCircle } from "lucide-react";

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
        <AlertCircle size={16} color="var(--primary-color)" />
        <span>Jenkins AI</span>
      </div>
      <div style={chatbotStyles.toastContent}>
        It looks like the build failed. Would you like me to analyze the console output for you?
      </div>
      <div style={chatbotStyles.toastActions}>
        <button style={chatbotStyles.toastCancelButton} onClick={onDismiss}>
          Not now
        </button>
        <button style={chatbotStyles.toastConfirmButton} onClick={onConfirm}>
          Yes, analyze
        </button>
      </div>
    </div>
  );
};
