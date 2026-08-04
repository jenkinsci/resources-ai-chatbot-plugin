interface ProactiveToastProps {
  onConfirm: () => void;
  onDismiss: () => void;
}

export const ProactiveToast = ({
  onConfirm,
  onDismiss,
}: ProactiveToastProps) => {
  return (
    <div className="toast-container">
      <div className="toast-header">
        <span>🤖 Jenkins Assistant</span>
      </div>
      <div className="toast-content">
        I detected a build failure. Would you like me to analyze the logs for you?
      </div>
      <div className="toast-actions">
        <button className="toast-btn toast-btn-cancel" onClick={onDismiss}>
          No
        </button>
        <button className="toast-btn toast-btn-confirm" onClick={onConfirm}>
          Yes, analyze
        </button>
      </div>
    </div>
  );
};
