import React, { useEffect, useRef } from "react";
import { type Message, type Sender } from "../model/Message";
import { chatbotStyles } from "../styles/styles";
import { getChatbotText } from "../data/chatbotTexts";

/**
 * Props for the Messages component.
 */
interface MessagesProps {
  messages: Message[];
  loading: boolean;
}

/**
 * Messages is responsible for rendering the chat conversation thread,
 * including both user and bot messages. It also displays the loading message
 * message when the bot is generating a response and automatically scrolls
 * to the newest message on update.
 */
export const Messages = ({ messages, loading }: MessagesProps) => {
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const renderMessage = (text: string, sender: Sender, key: React.Key) => (
    <div key={key} style={chatbotStyles.messageContainer(sender)}>
      <span style={chatbotStyles.messageBubble(sender)}>
        {text.split("\n").map((line, i) => (
          <React.Fragment key={i}>
            {line}
            <br />
          </React.Fragment>
        ))}
      </span>
    </div>
  );

  return (
    <div style={chatbotStyles.messagesMain}>
      {messages.map((msg) => renderMessage(msg.text, msg.sender, msg.id))}
      {loading &&
        renderMessage(
          getChatbotText("generatingMessage"),
          "jenkins-bot",
          "loading",
        )}
      <div ref={messagesEndRef} />
    </div>
  );
};
