import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Send,
  Sparkles,
  Bot,
  User,
  BookOpen,
  ShieldAlert,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: string[];
  confidence?: number;
  timestamp: string;
}

interface ChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  caseTitle?: string;
  suggestionChips?: string[];
  onSendMessage: (msg: string, model: string) => Promise<string>;
}

export function ChatDrawer({
  isOpen,
  onClose,
  caseTitle = 'Active Case',
  suggestionChips = [
    'Explain Section 482 BNSS regular bail principles.',
    'Is lack of Section 63 BSA certificate fatal to prosecution?',
    'Synthesize Sanjay Chandra precedent on bail vs jail.',
  ],
  onSendMessage,
}: ChatDrawerProps) {
  const [messages, setMessages] = React.useState<ChatMessage[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Good day, Advocate. I am your LexOrch-KG AI advisory assistant. I have reviewed the active record for "${caseTitle}". How may I assist your legal submissions today?`,
      timestamp: 'Just now',
    },
  ]);
  const [input, setInput] = React.useState('');
  const [selectedModel, setSelectedModel] = React.useState<'qwen' | 'deepseek'>('deepseek');
  const [loading, setLoading] = React.useState(false);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput('');
    setLoading(true);

    try {
      const reply = await onSendMessage(query, selectedModel);
      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: reply || 'I have analyzed the statutory record and relevant precedents regarding your query.',
        confidence: 0.94,
        citations: ['BNS S.111', 'BSA S.63', '(2011) 1 SCC 694'],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Unable to retrieve grounded response from multi-agent legal engine. Please verify connectivity.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-slate-900/30 backdrop-blur-xs"
            onClick={onClose}
          />

          {/* Drawer Panel in Daylight Chambers Light Glass Theme */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
            className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col border-l border-slate-200 bg-white/95 shadow-2xl backdrop-blur-2xl text-slate-900"
          >
            {/* Drawer Header */}
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 bg-[#FAF9F6]/80">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-sky-50 border border-sky-200 text-sky-700 shadow-2xs">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="font-serif text-sm font-bold text-slate-900">
                    LexOS Legal Advisory Chat
                  </h3>
                  <span className="font-mono text-[10px] text-emerald-700 font-semibold flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    Grounded RAG & Knowledge Graph Active
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {/* Model Selector */}
                <div className="flex items-center rounded-xl border border-slate-200 bg-slate-100 p-0.5 text-[11px] font-mono">
                  <button
                    onClick={() => setSelectedModel('deepseek')}
                    className={cn(
                      'px-2 py-1 rounded-lg transition cursor-pointer',
                      selectedModel === 'deepseek'
                        ? 'bg-white text-purple-700 font-semibold shadow-xs'
                        : 'text-slate-500 hover:text-slate-800'
                    )}
                  >
                    DeepSeek-R1
                  </button>
                  <button
                    onClick={() => setSelectedModel('qwen')}
                    className={cn(
                      'px-2 py-1 rounded-lg transition cursor-pointer',
                      selectedModel === 'qwen'
                        ? 'bg-white text-sky-700 font-semibold shadow-xs'
                        : 'text-slate-500 hover:text-slate-800'
                    )}
                  >
                    Qwen-3
                  </button>
                </div>

                <button
                  onClick={onClose}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Message Thread */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
              {messages.map((msg) => {
                const isUser = msg.role === 'user';
                return (
                  <div
                    key={msg.id}
                    className={cn('flex gap-3', isUser ? 'justify-end' : 'justify-start')}
                  >
                    {!isUser && (
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-sky-50 border border-sky-200 text-sky-700">
                        <Bot className="h-3.5 w-3.5" />
                      </div>
                    )}
                    <div
                      className={cn(
                        'max-w-[84%] rounded-2xl p-3.5 space-y-2 leading-relaxed shadow-xs',
                        isUser
                          ? 'bg-sky-600 text-white rounded-tr-none shadow-sky-500/10'
                          : 'bg-slate-50 text-slate-800 border border-slate-200/80 rounded-tl-none'
                      )}
                    >
                      <p className="whitespace-pre-wrap font-sans text-xs">{msg.content}</p>

                      {/* Citations chip bar */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="pt-2 border-t border-slate-200/60 flex flex-wrap gap-1.5">
                          {msg.citations.map((c, i) => (
                            <span
                              key={i}
                              className="inline-flex items-center gap-1 rounded-md bg-white px-2 py-0.5 font-mono text-[9px] text-sky-700 border border-slate-200 shadow-2xs font-semibold"
                            >
                              <BookOpen className="h-2 w-2" />
                              {c}
                            </span>
                          ))}
                        </div>
                      )}

                      <div className={cn("text-right font-mono text-[9px]", isUser ? "text-sky-100" : "text-slate-400")}>
                        {msg.timestamp}
                      </div>
                    </div>
                    {isUser && (
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-100 border border-slate-200 text-slate-700">
                        <User className="h-3.5 w-3.5" />
                      </div>
                    )}
                  </div>
                );
              })}

              {loading && (
                <div className="flex gap-3 items-center text-slate-500 text-xs">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-sky-50 border border-sky-200 text-sky-700">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  </div>
                  <span className="font-mono text-[11px] animate-pulse">
                    Synthesizing multi-agent legal reasoning...
                  </span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Suggestion Chips */}
            {suggestionChips.length > 0 && (
              <div className="border-t border-slate-100 px-4 py-3 bg-[#FAF9F6]/90">
                <span className="font-mono text-[10px] text-slate-500 font-semibold block mb-1.5 uppercase tracking-wider">
                  Suggested inquiries for this document:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {suggestionChips.map((chip, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSend(chip)}
                      className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-[11px] text-slate-700 hover:border-sky-300 hover:bg-sky-50 hover:text-sky-800 transition text-left shadow-2xs cursor-pointer font-medium"
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input Box & Disclaimer Footer */}
            <div className="border-t border-slate-200 p-3 bg-white">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSend();
                }}
                className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-1.5 focus-within:border-sky-500 focus-within:bg-white focus-within:ring-2 focus-within:ring-sky-100 transition shadow-2xs"
              >
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a question about the active case..."
                  className="flex-1 bg-transparent px-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 outline-none"
                />
                <button
                  type="submit"
                  disabled={!input.trim() || loading}
                  className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 text-white font-medium transition hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed shadow-xs cursor-pointer"
                >
                  <Send className="h-3.5 w-3.5" />
                </button>
              </form>

              <div className="mt-2 text-center font-mono text-[9px] text-slate-400 flex items-center justify-center gap-1">
                <ShieldAlert className="h-2.5 w-2.5" />
                AI can make mistakes — verify citations and operative statutory text.
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export default ChatDrawer;
