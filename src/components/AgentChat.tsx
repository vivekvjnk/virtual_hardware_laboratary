import { useState, useEffect, useRef } from 'react';

interface Message {
  id: string;
  sender: string;
  payload: {
    text: string;
  };
  timestamp: string;
}

export default function AgentChat({ moduleName, agentType, onClose, isEmbedded = false }: { moduleName: string, agentType: string, onClose: () => void, isEmbedded?: boolean }) {
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

  const containerClasses = isEmbedded
    ? "bg-slate-900 border border-slate-800 rounded-3xl w-full h-full flex flex-col shadow-2xl overflow-hidden"
    : "bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-2xl h-[600px] flex flex-col shadow-2xl overflow-hidden";

  return (
    <div className={isEmbedded ? "w-full h-full" : "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"}>
      <div className={containerClasses}>
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-800/50">
          <div>
            <h2 className="text-white font-bold text-lg">Chat with {agentType.charAt(0).toUpperCase() + agentType.slice(1)}</h2>
            <p className="text-slate-400 text-xs">{moduleName}</p>
          </div>
          {!isEmbedded && (
            <button 
              onClick={onClose}
              className="text-slate-400 hover:text-white transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Messages */}
        <div className="flex-grow overflow-y-auto p-4 space-y-4 bg-slate-900/50">
          {messages.length === 0 ? (
            <div className="text-center text-slate-500 mt-10">No messages yet. Start the conversation!</div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.sender === 'HIL' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] p-3 rounded-2xl ${
                  msg.sender === 'HIL' 
                    ? 'bg-blue-600 text-white rounded-tr-none' 
                    : 'bg-slate-800 text-slate-200 rounded-tl-none'
                }`}>
                  <div className="text-xs font-bold mb-1 opacity-70">{msg.sender}</div>
                  <div className="whitespace-pre-wrap">{msg.payload.text}</div>
                  <div className="text-[10px] mt-1 opacity-50 text-right">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={sendMessage} className="p-4 border-t border-slate-800 bg-slate-800/30">
          <div className="flex gap-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="bg-slate-700 hover:bg-slate-600 text-white font-bold py-2 px-4 rounded-xl transition-colors"
            >
              {file ? '📄' : '📎'}
            </button>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Message ${agentType}...`}
              className="flex-grow bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || (!input.trim() && !file)}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 text-white font-bold py-2 px-6 rounded-xl transition-colors"
            >
              {loading ? '...' : 'Send'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
