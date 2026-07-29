import { useState, useEffect, useRef } from 'react';
import MarkdownRenderer from './MarkdownRenderer';

interface Message {
  id: string;
  sender: string;
  payload: {
    text: string;
  };
  timestamp: string;
}

export default function AgentChat({ 
  moduleName, 
  agentType, 
  onClose, 
  isEmbedded = false
}: { 
  moduleName: string; 
  agentType: string; 
  onClose: () => void; 
  isEmbedded?: boolean; 
  initialMessage?: string; 
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const agentId = `${moduleName}.${agentType}`;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    // scrollToBottom();
  }, [messages]);

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(id);
      setTimeout(() => {
        setCopiedId(null);
      }, 2000);
    }).catch((err) => {
      console.error('Failed to copy text: ', err);
    });
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [input]);

  useEffect(() => {
    const fetchMessages = async () => {
      try {
        const response = await fetch(`http://localhost:3022/api/agents/${agentId}/messages`);
        const data = await response.json();
        if (data.messages) {
          setMessages(data.messages);
        }
      } catch (err) {
        console.error('Error fetching messages:', err);
      }
    };

    fetchMessages();
    const interval = setInterval(fetchMessages, 2000);
    return () => clearInterval(interval);
  }, [agentId]);

  const sendMessage = async (e?: React.FormEvent | React.KeyboardEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() && !file) return;

    setLoading(true);
    let filePath = null;

    try {
      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        const response = await fetch(`http://localhost:3022/api/upload-file`, {
          method: 'POST',
          body: formData
        });
        if (response.ok) {
          const data = await response.json();
          filePath = data.path;
        }
      }

      const response = await fetch(`http://localhost:3022/api/agents/${agentId}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: input, file_path: filePath })
      });

      if (response.ok) {
        setInput('');
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';

        // Optimistically add message
        const newMessage: Message = {
            id: Date.now().toString(),
            sender: 'HIL',
            payload: { text: file ? `[File: ${file.name}] ${input}` : input },
            timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, newMessage]);
      }
    } catch (err) {
      console.error('Error sending message:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(e);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isDisabled) {
        sendMessage(e);
      }
    }
  };

  const isDisabled = loading || (!input.trim() && !file);

  const wrapperStyle: React.CSSProperties = isEmbedded
    ? { 
        width: '100%', 
        height: '100%',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0
      }
    : {
        position: 'fixed',
        inset: 0,
        backgroundColor: '#020617',
        display: 'flex',
        flexDirection: 'column',
        padding: '0.75rem',
        zIndex: 50
      };

  const containerStyle: React.CSSProperties = {
    backgroundColor: isEmbedded ? 'transparent' : '#0f172a',
    border: isEmbedded ? 'none' : '1px solid #1e293b',
    borderRadius: isEmbedded ? 0 : '1rem',
    width: '100%',
    height: '100%',
    maxWidth: 'none',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    flex: 1,
    minHeight: 0
  };

  return (
    <div style={wrapperStyle}>
      <div style={containerStyle}>
        {/* Header - Only shown when NOT embedded */}
        {!isEmbedded && (
          <div style={{
            padding: '0.75rem 1.25rem',
            borderBottom: '1px solid #1e293b',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: '#0f172a'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                backgroundColor: '#020617',
                padding: '0.25rem 0.75rem',
                borderRadius: '0.5rem',
                border: '1px solid #1e293b'
              }}>
                <span style={{ color: '#64748b', fontSize: '0.7rem', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                  AGENT CHAT
                </span>
                <span style={{ color: '#334155', fontSize: '0.75rem' }}>/</span>
                <span style={{ color: '#60a5fa', fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                  {agentType}
                </span>
                <span style={{ color: '#334155', fontSize: '0.75rem' }}>/</span>
                <span style={{ color: '#38bdf8', fontSize: '0.75rem', fontWeight: 600, fontFamily: 'monospace' }}>
                  {moduleName}
                </span>
              </div>
            </div>
            <button 
              onClick={onClose}
              style={{
                backgroundColor: '#1e293b',
                color: '#ffffff',
                fontWeight: 600,
                padding: '0.375rem 0.875rem',
                borderRadius: '0.5rem',
                border: '1px solid #334155',
                cursor: 'pointer',
                fontSize: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.375rem',
                transition: 'all 0.2s ease'
              }}
            >
              <span>✕</span> Close
            </button>
          </div>
        )}

        {/* Messages Body */}
        <div style={{
          flexGrow: 1,
          minHeight: 0,
          overflowY: 'auto',
          padding: isEmbedded ? '0.75rem' : '1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: isEmbedded ? '0.75rem' : '1rem',
          backgroundColor: '#020617',
          borderRadius: isEmbedded ? '0.75rem' : 0
        }}>
          {messages.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#64748b', marginTop: '2.5rem', fontSize: '0.875rem' }}>
              No messages yet. Start the conversation!
            </div>
          ) : (
            messages.map((msg, index) => {
              const isHIL = msg.sender === 'HIL';
              const msgKey = msg.id ? `${msg.id}-${index}` : `${index}`;
              return (
                <div key={msgKey} style={{ display: 'flex', justifyContent: isHIL ? 'flex-end' : 'flex-start' }}>
                  <div style={{
                    maxWidth: isEmbedded ? '88%' : '80%',
                    padding: isEmbedded ? '0.625rem 0.75rem' : '0.75rem',
                    borderRadius: isEmbedded ? '0.75rem' : '1rem',
                    borderTopRightRadius: isHIL ? 0 : (isEmbedded ? '0.75rem' : '1rem'),
                    borderTopLeftRadius: isHIL ? (isEmbedded ? '0.75rem' : '1rem') : 0,
                    backgroundColor: isHIL ? '#2563eb' : '#1e293b',
                    color: isHIL ? '#ffffff' : '#e2e8f0',
                    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.2)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.375rem', gap: '0.75rem' }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 'bold', opacity: 0.7 }}>
                        {msg.sender}
                      </div>
                      {!isHIL && (
                        <button
                          type="button"
                          onClick={() => handleCopy(msgKey, msg.payload.text)}
                          title="Copy raw markdown"
                          style={{
                            background: 'none',
                            border: 'none',
                            color: copiedId === msgKey ? '#4ade80' : '#94a3b8',
                            cursor: 'pointer',
                            fontSize: '0.7rem',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.125rem 0.375rem',
                            borderRadius: '0.25rem',
                            backgroundColor: 'rgba(255, 255, 255, 0.08)',
                            transition: 'all 0.2s ease'
                          }}
                        >
                          {copiedId === msgKey ? (
                            <>
                              <span>✓</span> Copied
                            </>
                          ) : (
                            <>
                              <span>📋</span> Copy
                            </>
                          )}
                        </button>
                      )}
                    </div>
                    <div style={{ fontSize: '0.875rem', lineHeight: '1.25rem' }}>
                      <MarkdownRenderer content={msg.payload.text} />
                    </div>
                    <div style={{ fontSize: '0.625rem', marginTop: '0.25rem', opacity: 0.5, textAlign: 'right' }}>
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              );
            })
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} style={{
          padding: isEmbedded ? '0.5rem 0 0 0' : '0.75rem 1rem',
          borderTop: isEmbedded ? 'none' : '1px solid #1e293b',
          backgroundColor: isEmbedded ? 'transparent' : '#0f172a'
        }}>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end' }}>
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
              style={{ display: 'none' }}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              style={{ 
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.55rem 0.75rem', 
                borderRadius: '0.75rem', 
                fontSize: '0.75rem', 
                fontWeight: 600, 
                textTransform: 'uppercase', 
                letterSpacing: '0.05em',
                cursor: 'pointer',
                backgroundColor: 'rgba(37, 99, 235, 0.15)',
                border: '1px solid rgba(59, 130, 246, 0.5)',
                color: '#60a5fa',
                boxShadow: '0 0 2px rgba(59, 130, 246, 0.2)',
                transition: 'all 0.2s ease',
                marginBottom: '1px'
              }}
            >
              {file ? '📄' : '📎'}
            </button>
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Message ${agentType}...`}
              style={{
                flexGrow: 1,
                backgroundColor: '#020617',
                border: '1px solid #334155',
                borderRadius: '0.75rem',
                padding: '0.5rem 1rem',
                color: '#ffffff',
                outline: 'none',
                fontSize: '0.875rem',
                resize: 'none',
                maxHeight: '140px',
                overflowY: 'auto',
                fontFamily: 'inherit',
                lineHeight: '1.4'
              }}
              disabled={loading}
            />
            <button
              type="submit"
              disabled={isDisabled}
              style={{ 
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.55rem 1rem', 
                borderRadius: '0.75rem', 
                fontSize: '0.75rem', 
                fontWeight: 600, 
                textTransform: 'uppercase', 
                letterSpacing: '0.05em',
                cursor: 'pointer',
                backgroundColor: 'rgba(37, 99, 235, 0.15)',
                border: '1px solid rgba(59, 130, 246, 0.5)',
                color: '#60a5fa',
                boxShadow: '0 0 2px rgba(59, 130, 246, 0.2)',
                transition: 'all 0.2s ease',
                marginBottom: '1px'
              }}
            >
              {loading ? '...' : 'Send'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}