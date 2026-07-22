import { useState, useEffect, useRef } from 'react';

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
  isEmbedded = false, 
  initialMessage 
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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const agentId = `${moduleName}.${agentType}`;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    // scrollToBottom();
  }, [messages]);

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

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
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
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
        zIndex: 50
      };

  const containerStyle: React.CSSProperties = {
    backgroundColor: '#020617',
    border: '3px solid #1e293b',
    borderRadius: isEmbedded ? '0.75rem' : '1.5rem',
    width: '100%',
    height: isEmbedded ? '100%' : '600px',
    maxWidth: isEmbedded ? 'none' : '42rem',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: isEmbedded ? 'none' : '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
    overflow: 'hidden',
    flex: 1
  };

  return (
    <div style={wrapperStyle}>
      <div style={containerStyle}>
        {/* Header - Only shown when NOT embedded */}
        {!isEmbedded && (
          <div style={{
            padding: '1rem',
            borderBottom: '1px solid #1e293b',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: '#0f172a'
          }}>
            <div>
              <h2 style={{ color: '#ffffff', fontWeight: 'bold', fontSize: '1.125rem', margin: 0 }}>
                Chat with {agentType.charAt(0).toUpperCase() + agentType.slice(1)}
              </h2>
              <p style={{ color: '#94a3b8', fontSize: '0.75rem', margin: 0 }}>{moduleName}</p>
            </div>
            <button 
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '0.25rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" style={{ height: '1.5rem', width: '1.5rem' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Messages Body */}
        <div style={{
          flexGrow: 1,
          overflowY: 'auto',
          padding: '1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          backgroundColor: '#020617'
        }}>
          {messages.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#64748b', marginTop: '2.5rem', fontSize: '0.875rem' }}>
              No messages yet. Start the conversation!
            </div>
          ) : (
            messages.map((msg) => {
              const isHIL = msg.sender === 'HIL';
              return (
                <div key={msg.id} style={{ display: 'flex', justifyContent: isHIL ? 'flex-end' : 'flex-start' }}>
                  <div style={{
                    maxWidth: '80%',
                    padding: '0.75rem',
                    borderRadius: '1rem',
                    borderTopRightRadius: isHIL ? 0 : '1rem',
                    borderTopLeftRadius: isHIL ? '1rem' : 0,
                    backgroundColor: isHIL ? '#2563eb' : '#1e293b',
                    color: isHIL ? '#ffffff' : '#e2e8f0',
                    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.2)'
                  }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 'bold', marginBottom: '0.25rem', opacity: 0.7 }}>
                      {msg.sender}
                    </div>
                    <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.875rem', lineHeight: '1.25rem' }}>
                      {msg.payload.text}
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
          padding: '0.75rem 1rem',
          borderTop: '1px solid #1e293b',
          backgroundColor: '#0f172a'
        }}>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
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
                padding: '0.5rem 0.75rem', 
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
                transition: 'all 0.2s ease'
              }}
            >
              {file ? '📄' : '📎'}
            </button>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Message ${agentType}...`}
              style={{
                flexGrow: 1,
                backgroundColor: '#020617',
                border: '1px solid #334155',
                borderRadius: '0.75rem',
                padding: '0.5rem 1rem',
                color: '#ffffff',
                outline: 'none',
                fontSize: '0.875rem'
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
                padding: '0.5rem 1rem', 
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
                transition: 'all 0.2s ease'
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