import { chatbotStyles } from "../styles/styles";

export const LoadingDots = () => {
  return (
    <div style={chatbotStyles.loadingContainer}>
      <span style={{ ...chatbotStyles.loadingDot1 }}>•</span>
      <span style={{ ...chatbotStyles.loadingDot2 }}>•</span>
      <span style={{ ...chatbotStyles.loadingDot3 }}>•</span>
    </div>
  );
};
