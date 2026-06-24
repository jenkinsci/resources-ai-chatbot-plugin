import React from "react";
export const TypingIndicator = () => {
  return (
    <div className="typing-dots-wrapper">
      <span className="typing-dot" style={{ animationDelay: '0ms' }} />
      <span className="typing-dot" style={{ animationDelay: '200ms' }} />
      <span className="typing-dot" style={{ animationDelay: '400ms' }} />
    </div>
  });
};
