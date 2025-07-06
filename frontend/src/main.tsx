import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Chatbot } from "./components/Chatbot";

const footerRoot = document.getElementById("chatbot-root")!;

createRoot(footerRoot).render(
  <StrictMode>
    <Chatbot />
  </StrictMode>,
);
