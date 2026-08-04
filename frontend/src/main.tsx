import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MinimalChatbot } from "./components/MinimalChatbot";
import "./index.css";

const rootElement = document.getElementById("chatbot-root")!;
createRoot(rootElement).render(
  <StrictMode>
    <MinimalChatbot />
  </StrictMode>
);
