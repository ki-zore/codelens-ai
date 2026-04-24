import { useState, useRef, useEffect } from 'react';
import { useApp } from '../../store/AppContext';
import { api } from '../../services/api';
import ReactMarkdown from 'react-markdown';
import { Send, Loader2, Sparkles, FileCode, Trash2 } from 'lucide-react';

export default function ChatPanel() {
  const { activeProject, chatHistory, addMessage, clearChat, setActiveFile } = useApp();
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatHistory]);

  const handleSend = async () => {
    if (!input.trim() || !activeProject || streaming) return;
    const question = input.trim();
    setInput('');
    addMessage({ role: 'user', content: question });
    setStreaming(true);

    let answer = '';
    let refs = [];
    addMessage({ role: 'assistant', content: '', references: [], streaming: true });

    try {
      await api.queryStream(activeProject.project_id, question, 5, (chunk) => {
        if (chunk.type === 'text') {
          answer += chunk.content;
          addMessage(null); // trigger re-render hack
        } else if (chunk.type === 'references') {
          refs = chunk.references || [];
        }
      });
    } catch (e) {
      answer = `Error: ${e.message}`;
    }

    // Replace last message with final
    addMessage({ role: 'assistant', content: answer, references: refs, streaming: false, replace: true });
    setStreaming(false);
    inputRef.current?.focus();
  };

  // Build display messages (handle streaming updates)
  const messages = [];
  let lastAssistant = null;
  for (const m of chatHistory) {
    if (m === null) continue;
    if (m.replace && lastAssistant !== null) {
      messages[lastAssistant] = m;
    } else {
      messages.push(m);
      if (m.role === 'assistant') lastAssistant = messages.length - 1;
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-accent" />
          <span className="text-sm font-semibold text-text-primary">AI Chat</span>
          {activeProject && (
            <span className="badge bg-accent/15 text-accent">{activeProject.name}</span>
          )}
        </div>
        {messages.length > 0 && (
          <button onClick={clearChat} className="p-1.5 rounded hover:bg-dark-600 text-text-muted hover:text-rose transition-colors">
            <Trash2 size={14} />
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent/20 to-cyan/20 flex items-center justify-center mb-4">
              <Sparkles size={28} className="text-accent" />
            </div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">Ask about your codebase</h3>
            <p className="text-sm text-text-muted max-w-md">
              {activeProject
                ? 'Ask questions about code structure, debug issues, or explore dependencies.'
                : 'Select or add a project to get started.'}
            </p>
            {activeProject && (
              <div className="mt-4 flex flex-wrap gap-2 justify-center">
                {['What does this project do?', 'Show me the main entry point', 'Find potential bugs'].map(q => (
                  <button key={q} onClick={() => { setInput(q); }}
                    className="px-3 py-1.5 text-xs rounded-full border border-border text-text-secondary
                      hover:border-accent/50 hover:text-accent transition-colors">
                    {q}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
              msg.role === 'user'
                ? 'bg-accent text-white rounded-br-md'
                : 'glass-panel rounded-bl-md'
            }`}>
              {msg.role === 'assistant' ? (
                <div className="prose prose-invert prose-sm max-w-none
                  [&_pre]:bg-dark-900 [&_pre]:rounded-lg [&_pre]:p-3 [&_pre]:text-xs
                  [&_code]:text-cyan [&_code]:text-xs [&_a]:text-accent">
                  <ReactMarkdown>{msg.content || (msg.streaming ? '...' : '')}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-sm">{msg.content}</p>
              )}
              {msg.references?.length > 0 && (
                <div className="mt-3 pt-3 border-t border-border/50 space-y-1">
                  <span className="text-xs text-text-muted font-medium">References:</span>
                  {msg.references.map((ref, j) => (
                    <button key={j}
                      onClick={() => setActiveFile({ path: ref.file_path, line: ref.start_line })}
                      className="flex items-center gap-1.5 text-xs text-accent hover:text-accent-light transition-colors">
                      <FileCode size={12} />
                      {ref.file_path}:{ref.start_line}-{ref.end_line}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-border shrink-0">
        <div className="flex gap-2 items-end">
          <textarea ref={inputRef} value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder={activeProject ? "Ask about the codebase..." : "Select a project first..."}
            disabled={!activeProject || streaming}
            rows={1}
            className="flex-1 px-4 py-3 bg-dark-700 border border-border rounded-xl text-sm text-text-primary
              placeholder:text-text-muted resize-none focus:outline-none focus:border-accent transition-colors
              disabled:opacity-50" />
          <button onClick={handleSend} disabled={!input.trim() || !activeProject || streaming}
            className="btn-primary p-3 rounded-xl shrink-0">
            {streaming ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
          </button>
        </div>
      </div>
    </div>
  );
}
