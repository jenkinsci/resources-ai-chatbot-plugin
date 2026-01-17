import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Chatbot } from "./components/Chatbot";

const footerRoot = document.getElementById("chatbot-root")!;

if (footerRoot) {
  createRoot(footerRoot).render(
    <StrictMode>
      <Chatbot />
    </StrictMode>,
  );
} else {
  console.error("Chatbot root element not found in Jenkins page!");
}
