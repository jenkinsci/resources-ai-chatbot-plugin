import { useState, useEffect } from 'react';
import { type Message } from '../model/Message';
import { fetchChatbotReply } from '../api/chatbot';
import { Header } from './Header';
import { Messages } from './Messages';
import { Input } from './Input';
import { chatbotStyles } from '../styles/styles';
import { getChatbotText } from '../data/chatbotTexts';
import { v4 as uuidv4 } from 'uuid';

/**
 * Chatbot is the core component responsible for managing the chatbot display.
 */
export const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');

  /**
   * Messages shown in the chat.
   * Initialized from sessionStorage to keep messages between refreshes.
   */
  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = sessionStorage.getItem('chatbot-messages');
    return saved ? JSON.parse(saved) : [];
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    sessionStorage.setItem('chatbot-messages', JSON.stringify(messages));
  }, [messages]);

  const clearMessages = () => {
    setMessages([]);
    // Once backend is ready, add logic to clear history chat
  };

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed) return;

    const userMessage: Message = {
      id: uuidv4(),
      sender: 'user',
      text: trimmed,
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    const botReply = await fetchChatbotReply(trimmed);
    setLoading(false);
    setMessages(prev => [...prev, botReply]);
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={chatbotStyles.toggleButton}
      >
        {getChatbotText("toggleButtonLabel")}
      </button>

      {isOpen && (
        <div
           style={chatbotStyles.container}
        >
          <Header clearMessages={clearMessages} />
          <Messages messages={messages} loading={loading} />
          <Input input={input} setInput={setInput} onSend={sendMessage} />
        </div>
      )}
    </>
  );
};
