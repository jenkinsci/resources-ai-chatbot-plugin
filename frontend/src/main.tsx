import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Chatbot } from "./components/Chatbot";
import "./index.css";

const footerRoot = document.getElementById("chatbot-root");

if (!footerRoot) {
  throw new Error("Chatbot root element '#chatbot-root' was not found.");
}

createRoot(footerRoot).render(
  <StrictMode>
    <Chatbot />
  </StrictMode>,
);
