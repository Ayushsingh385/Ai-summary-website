import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import {
  FiMessageSquare,
  FiSend,
  FiFileText,
  FiUsers,
  FiDatabase,
  FiInfo,
  FiChevronDown
} from 'react-icons/fi';
import { chatWithBot } from '../api';

const QuickActions = ({ onAction, disabled }) => {
  const actions = [
    { label: 'Summarize', query: 'Summarize this document', icon: <FiFileText size={14} /> },
    { label: 'Key entities', query: 'What are the key entities in this document?', icon: <FiUsers size={14} /> },
    { label: 'Similar cases', query: 'Find similar cases', icon: <FiDatabase size={14} /> },
  ];

  return (
    <div className="chat-quick-actions" style={styles.quickActions}>
      {actions.map((action, idx) => (
        <motion.button
          key={idx}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => onAction(action.query)}
          disabled={disabled}
          style={styles.quickActionBtn}
        >
          {action.icon}
          <span style={{ marginLeft: '6px' }}>{action.label}</span>
        </motion.button>
      ))}
    </div>
  );
};

const ChatBot = ({ documentText, keywords }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'bot',
      text: 'Hi! I can help you understand your legal documents. Ask me anything about the current file, or use the quick actions below.'
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const chatRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) scrollToBottom();
  }, [messages, isOpen]);

  // Click outside handler
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (chatRef.current && !chatRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleSend = async (query) => {
    const messageText = query || input;
    if (!messageText.trim()) return;

    const userMessage = { id: Date.now(), role: 'user', text: messageText };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const data = await chatWithBot(messageText, documentText, keywords);
      const botMessage = { id: Date.now() + 1, role: 'bot', text: data.response };
      setMessages(prev => [...prev, botMessage]);

      // Message received
    } catch (err) {
      const errorMsg = {
        id: Date.now() + 1,
        role: 'bot',
        text: 'Sorry, I encountered an error. Please check your connection and try again.'
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    handleSend();
  };

  return (
    <>
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setIsOpen(true)}
            style={styles.floatingButton}
            aria-label="Open chat"
          >
            <FiMessageSquare size={22} />
            <span style={{ marginLeft: '12px', fontWeight: '600', fontSize: '0.95rem' }}>
              Ask Legal Assistant
            </span>
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ y: 100, opacity: 0, scale: 0.9 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 100, opacity: 0, scale: 0.9 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            ref={chatRef}
            style={styles.chatContainer}
          >
            <div style={styles.chatHeader}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={styles.headerIcon}>
                  <FiMessageSquare size={18} />
                </div>
                <div>
                  <div style={styles.headerTitle}>Legal Assistant</div>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                style={styles.closeBtn}
                aria-label="Close chat"
              >
                <FiChevronDown size={24} />
              </button>
            </div>

            <div style={styles.messagesContainer}>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, x: msg.role === 'user' ? 20 : -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.05 }}
                  style={{
                    ...styles.messageWrapper,
                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
                  }}
                >
                  <div
                    style={{
                      ...styles.messageBubble,
                      background: msg.role === 'user' ? 'var(--accent-primary)' : 'rgba(255, 255, 255, 0.05)',
                      backdropFilter: msg.role !== 'user' ? 'blur(10px)' : 'none',
                      border: msg.role !== 'user' ? '1px solid rgba(255, 255, 255, 0.1)' : 'none',
                      color: msg.role === 'user' ? '#ffffff' : 'var(--text-main)',
                      boxShadow: msg.role === 'user' ? '0 4px 15px rgba(56, 189, 248, 0.3)' : 'none'
                    }}
                  >
                    <div className="markdown-content" style={{ fontSize: '0.96rem', lineHeight: '1.6' }}>
                      {msg.text ? (
                        <ReactMarkdown>{String(msg.text)}</ReactMarkdown>
                      ) : (
                        <span>...</span>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  style={{ ...styles.messageWrapper, justifyContent: 'flex-start' }}
                >
                  <div style={{ ...styles.messageBubble, background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', color: 'var(--text-muted)' }}>
                    <div style={styles.typingIndicator}>
                      <span style={styles.typingDot}></span>
                      <span style={styles.typingDot}></span>
                      <span style={styles.typingDot}></span>
                    </div>
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div style={styles.footer}>
              {!documentText && (
                <div style={styles.hint}>
                  <FiInfo size={14} />
                  <span style={{ marginLeft: '6px' }}>Upload a document for context-aware answers</span>
                </div>
              )}

              <QuickActions onAction={handleSend} disabled={isLoading || !documentText} />

              <form onSubmit={handleSubmit} style={styles.inputArea}>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask me anything..."
                  style={styles.input}
                  disabled={isLoading}
                />
                <motion.button
                  type="submit"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  disabled={!input.trim() || isLoading}
                  style={{
                    ...styles.sendBtn,
                    opacity: (!input.trim() || isLoading) ? 0.5 : 1
                  }}
                >
                  <FiSend size={18} />
                </motion.button>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

const styles = {
  floatingButton: {
    bottom: '2.5rem',
    right: '1.75rem',
    zIndex: 9999,
    height: '56px',
    padding: '0 1.75rem',
    borderRadius: '28px',
    background: 'var(--accent-primary)',
    color: '#fff',
    border: 'none',
    cursor: 'pointer',
    boxShadow: '0 8px 30px rgba(56, 189, 248, 0.4)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '4px',
    position: 'fixed'
  },
  chatContainer: {
    position: 'fixed',
    bottom: '2rem',
    right: '1.75rem',
    zIndex: 9999,
    width: '480px',
    height: 'min(850px, 85vh)',
    display: 'flex',
    flexDirection: 'column',
    background: 'rgba(15, 23, 42, 0.85)',
    backdropFilter: 'blur(16px) saturate(180%)',
    borderRadius: '24px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    boxShadow: '0 20px 50px rgba(0, 0, 0, 0.5)',
    overflow: 'hidden'
  },
  chatHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '1.25rem 1.5rem',
    background: 'rgba(255, 255, 255, 0.03)',
    borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
    color: 'var(--text-main)'
  },
  headerIcon: {
    width: '36px',
    height: '36px',
    borderRadius: '10px',
    background: 'var(--accent-primary)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#fff'
  },
  headerTitle: {
    fontSize: '1rem',
    fontWeight: '700'
  },
  headerStatus: {
    fontSize: '0.7rem',
    color: 'var(--accent-primary)',
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
  },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer'
  },
  messagesContainer: {
    flex: 1,
    padding: '2.5rem 2.25rem',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '2.5rem'
  },
  messageWrapper: {
    display: 'flex',
    width: '100%'
  },
  messageBubble: {
    maxWidth: '88%',
    padding: '1.25rem 1.5rem',
    borderRadius: '22px',
    fontSize: '0.96rem',
    lineHeight: '1.6'
  },
  footer: {
    background: 'rgba(15, 23, 42, 0.4)',
    borderTop: '1px solid rgba(255, 255, 255, 0.08)'
  },
  hint: {
    padding: '0.75rem 1.25rem',
    fontSize: '0.75rem',
    color: 'var(--text-muted)',
    display: 'flex',
    alignItems: 'center'
  },
  quickActions: {
    display: 'flex',
    gap: '0.6rem',
    padding: '0.5rem 1.25rem',
    flexWrap: 'wrap'
  },
  quickActionBtn: {
    padding: '0.5rem 0.9rem',
    borderRadius: '12px',
    background: 'rgba(255, 255, 258, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    color: 'var(--text-main)',
    fontSize: '0.75rem',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center'
  },
  inputArea: {
    display: 'flex',
    padding: '1.75rem',
    gap: '1rem'
  },
  input: {
    flex: 1,
    padding: '1.1rem 1.3rem',
    borderRadius: '16px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    background: 'rgba(255, 255, 255, 0.03)',
    color: 'var(--text-main)',
    outline: 'none'
  },
  sendBtn: {
    background: 'var(--accent-primary)',
    color: '#fff',
    border: 'none',
    borderRadius: '12px',
    padding: '0 1.1rem',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 4px 15px rgba(56, 189, 248, 0.3)'
  },
  typingIndicator: {
    display: 'flex',
    gap: '4px',
    padding: '4px 0'
  },
  typingDot: {
    width: '6px',
    height: '6px',
    background: 'var(--text-muted)',
    borderRadius: '50%',
    display: 'inline-block',
    animation: 'typing 1.4s infinite ease-in-out'
  }
};

export default ChatBot;