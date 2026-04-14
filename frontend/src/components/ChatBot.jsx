import { useState, useRef, useEffect } from 'react';
import { FiMessageSquare, FiX, FiSend } from 'react-icons/fi';
import { chatWithBot } from '../api';

const ChatBot = ({ documentText, keywords }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { id: 1, role: 'bot', text: 'Hi there. I can help you read through this case. Just ask me to summarize it, find names, or look for other files like this one.' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) scrollToBottom();
  }, [messages, isOpen]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { id: Date.now(), role: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const data = await chatWithBot(userMessage.text, documentText, keywords);
      // Reformat simple bolding markdown for basic HTML display
      const formattedText = data.response.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      const botMessage = { id: Date.now() + 1, role: 'bot', text: formattedText };
      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      const errorMsg = { id: Date.now() + 1, role: 'bot', text: 'Sorry, I encountered an error connecting to the server.' };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        style={styles.floatingButton}
        className=""
      >
        <FiMessageSquare size={24} />
      </button>
    );
  }

  return (
    <div style={styles.chatContainer}>
      <div style={styles.chatHeader}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <FiMessageSquare /> <strong>Assistant</strong>
        </div>
        <button onClick={() => setIsOpen(false)} style={styles.closeBtn}><FiX size={20} /></button>
      </div>
      
      <div style={styles.messagesContainer}>
        {messages.map(msg => (
          <div key={msg.id} style={{
            ...styles.messageWrapper, 
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
          }}>
            <div style={{
              ...styles.messageBubble,
              background: msg.role === 'user' ? 'var(--accent-primary)' : 'var(--panel-bg)',
              border: msg.role !== 'user' ? '1px solid var(--panel-border)' : 'none',
              color: msg.role === 'user' ? '#ffffff' : 'var(--text-main)'
            }}>
              <span dangerouslySetInnerHTML={{__html: msg.text.replace(/\n/g, '<br/>')}} />
            </div>
          </div>
        ))}
        {isLoading && (
          <div style={{...styles.messageWrapper, justifyContent: 'flex-start'}}>
            <div style={{...styles.messageBubble, background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-muted)'}}>
              Reading...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSend} style={styles.inputArea}>
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask me anything about this file..."
          style={styles.input}
        />
        <button type="submit" disabled={!input.trim() || isLoading} style={styles.sendBtn}>
          <FiSend />
        </button>
      </form>
    </div>
  );
};

const styles = {
  floatingButton: {
    position: 'fixed', bottom: '2rem', right: '2rem', zIndex: 9999,
    width: '60px', height: '60px', borderRadius: '50%',
    background: 'var(--accent-primary)',
    color: '#fff', border: 'none', cursor: 'pointer',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)', display: 'flex',
    alignItems: 'center', justifyContent: 'center', transition: 'transform 0.1s ease'
  },
  chatContainer: {
    position: 'fixed', bottom: '2rem', right: '2rem', zIndex: 9999,
    width: '350px', height: '500px', display: 'flex', flexDirection: 'column',
    background: 'var(--bg-darker)', borderRadius: '12px',
    border: '1px solid var(--panel-border)', boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4)',
    overflow: 'hidden'
  },
  chatHeader: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '1rem', background: 'var(--panel-bg)',
    borderBottom: '1px solid var(--panel-border)', color: 'var(--text-main)'
  },
  closeBtn: {
    background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer'
  },
  messagesContainer: {
    flex: 1, padding: '1rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.8rem',
    background: 'transparent'
  },
  messageWrapper: {
    display: 'flex', width: '100%'
  },
  messageBubble: {
    maxWidth: '85%', padding: '0.75rem 1rem', borderRadius: '12px',
    fontSize: '0.9rem', lineHeight: '1.4'
  },
  inputArea: {
    display: 'flex', padding: '1rem', borderTop: '1px solid var(--panel-border)', gap: '0.5rem', background: 'var(--bg-darker)'
  },
  input: {
    flex: 1, padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--panel-border)',
    background: 'var(--bg-dark)', color: 'var(--text-main)', outline: 'none'
  },
  sendBtn: {
    background: 'var(--accent-primary)', color: '#fff', border: 'none', borderRadius: '8px',
    padding: '0 1rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center'
  }
};

export default ChatBot;
