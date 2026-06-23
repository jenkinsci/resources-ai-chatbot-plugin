import { useState } from "react";
import { Chatbot } from "./Chatbot";
import { MessageSquare } from "lucide-react";
import "../index.css";

export const MinimalChatbot = () => {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* FAB button when closed */}
      {!open && (
        <button
          className="fab-button"
          onClick={() => setOpen(true)}
          aria-label="Open chatbot"
        >
          <MessageSquare size={24} />
        </button>
      )}
      {/* Chat widget when open */}
      {open && (
        <div className="chat-widget-wrapper">
          <Chatbot onClose={() => setOpen(false)} />
        </div>
      )}
    </>
  );
};
