import { chatbotStyles } from "../styles/styles";

export const LoadingDots = () => {
  return (
    <div style={{ display: "flex", gap: "4px" }}>
      <div style={chatbotStyles.loadingDot1} />
      <div style={chatbotStyles.loadingDot2} />
      <div style={chatbotStyles.loadingDot3} />
    </div>
  );
};
