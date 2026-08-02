import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Loader2,
  StopCircle,
  Copy,
  Download,
  RotateCcw,
  Sparkles,
  Search,
  BookOpen,
  Scale,
  Brain,
  CheckCircle2,
  AlertCircle,
  ChevronRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/stores/appStore';

interface Source {
  id: string;
  act: string;
  section?: string;
  type: 'act' | 'precedent';
  text: string;
  score: number;
}

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  thinkingSteps?: string[];
  sources?: Source[];
  confidence?: number;
}

export default function ChatPage() {
  const [searchParams] = useSearchParams();
  const queryParam = searchParams.get('query');

  const { activeModel, agentStatus, setAgentStatus } = useAppStore();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'assistant',
      text: 'Hello! I am LexOrch-KG, your explainable legal AI advisory assistant. Ask me any question regarding Indian criminal codes (BNS, BNSS, BSA, IPC) or landmark precedents.',
    }
  ]);
  
  const [input, setInput] = useState('');
  const [streamingIndex, setStreamingIndex] = useState(-1);
  const [streamingText, setStreamingText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText]);

  // Handle URL query parameters if passed from dashboard quick search
  useEffect(() => {
    if (queryParam) {
      handleSendQuery(queryParam);
    }
  }, [queryParam]);

  const simulateStreamingResponse = (query: string) => {
    setAgentStatus('thinking');
    
    // Create mock answer data
    const isBailQuery = query.toLowerCase().includes('bail');
    
    const mockThinkingSteps = [
      'Extracting query semantic embedding using local BGE-M3 model...',
      'Performing vector lookup in legal_documents collection (Top-K=5)...',
      'Searching FalkorDB graph links for case-statute associations...',
      'Cross-referencing BNSS provisions with precedent definitions...',
      'Assembling facts and validating response structure...'
    ];

    const mockSources: Source[] = isBailQuery
      ? [
          { id: 'S1', act: 'BNSS, 2023', section: 'Section 482', type: 'act', text: 'Provisions as to bail in case of non-bailable offences. Under Section 482 of the Bharatiya Nagarik Suraksha Sanhita, 2023, a court or officer-in-charge may release an accused person on bail subject to conditions...', score: 0.89 },
          { id: 'S2', act: 'Supreme Court Case Law', type: 'precedent', text: 'Sanjay Chandra v. CBI (2012) landmark ruling. The Hon\'ble Supreme Court held that the grant of bail is the rule and committal to jail is an exception. Detention during trial is not punitive...', score: 0.82 }
        ]
      : [
          { id: 'S1', act: 'Constitution of India', section: 'Article 21', type: 'act', text: 'Protection of life and personal liberty. No person shall be deprived of his life or personal liberty except according to procedure established by law...', score: 0.94 },
          { id: 'S2', act: 'BNS, 2023', section: 'Section 103', type: 'act', text: 'Punishment for murder. Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine. Corresponds to old Section 302 of the IPC...', score: 0.87 }
        ];

    const fullResponse = isBailQuery
      ? `Under the new **Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023**, the provisions relating to bail for non-bailable offences are governed by **Section 482** [1]. 

Here are the key aspects:
1. **Conditions for Release**: A person accused of or suspected of the commission of any non-bailable offence may be released on bail, but they shall not be so released if there appear reasonable grounds for believing that they have been guilty of an offence punishable with death or imprisonment for life.
2. **Precedent Standard**: As reiterated by the Supreme Court in *Sanjay Chandra v. CBI* [2], bail is the general rule and prison is the exception, meaning pre-conviction detention should not be used as punishment.
3. **Special Powers**: High Courts and Courts of Session hold wider discretionary powers to impose custom bail conditions to guarantee the accused's presence at trial.`
      : `Under the **Indian Constitution**, your fundamental rights are anchored primarily under **Part III**. Specifically, **Article 21** [1] guarantees that *"no person shall be deprived of his life or personal liberty except according to procedure established by law"*. 

If you are querying criminal liability, **Section 103 of the Bharatiya Nyaya Sanhita (BNS), 2023** [2] defines the punishment for murder (formerly Section 302 of the IPC), providing for either death or life imprisonment, which must respect the procedure established under the constitution.`;

    let stepIndex = 0;
    const interval = setInterval(() => {
      if (stepIndex < mockThinkingSteps.length) {
        if (stepIndex === 1) setAgentStatus('analyzing');
        if (stepIndex === 3) setAgentStatus('verifying');
        
        // Append thinking logs to the active user UI
        stepIndex++;
      } else {
        clearInterval(interval);
        setAgentStatus('complete');
        
        // Start streaming text
        setStreamingText('');
        let charIndex = 0;
        const textStream = setInterval(() => {
          if (charIndex < fullResponse.length) {
            setStreamingText((prev) => prev + fullResponse.charAt(charIndex));
            charIndex += 4; // speed up stream
          } else {
            clearInterval(textStream);
            setAgentStatus('idle');
            setMessages((prev) => [
              ...prev,
              {
                id: Math.random().toString(),
                sender: 'assistant',
                text: fullResponse,
                thinkingSteps: mockThinkingSteps,
                sources: mockSources,
                confidence: isBailQuery ? 88.5 : 94.2
              }
            ]);
            setStreamingText('');
          }
        }, 15);
      }
    }, 800);
  };

  const handleSendQuery = (textToSend: string) => {
    if (!textToSend.trim()) return;
    
    // Add user message to stack
    setMessages((prev) => [
      ...prev,
      { id: Math.random().toString(), sender: 'user', text: textToSend }
    ]);
    setInput('');
    simulateStreamingResponse(textToSend);
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col bg-background">
      {/* MESSAGE STREAM AREA */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "flex flex-col gap-3 rounded-2xl p-5 border",
                msg.sender === 'user'
                  ? "bg-primary/5 border-primary/10 ml-auto max-w-[85%]"
                  : "bg-card/30 border-white/5 mr-auto w-full glass-panel"
              )}
            >
              {/* Sender Header */}
              <div className="flex items-center gap-2">
                <div className={cn("rounded-md p-1", msg.sender === 'user' ? "bg-primary/20 text-primary" : "bg-cyan-500/10 text-cyan-400")}>
                  <Brain className="h-4 w-4" />
                </div>
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  {msg.sender === 'user' ? 'Client Request' : `${activeModel.toUpperCase()} Legal Advisor`}
                </span>
                {msg.confidence && (
                  <span className="ml-auto text-xs bg-emerald-500/10 text-emerald-400 font-semibold px-2 py-0.5 rounded-full border border-emerald-500/20">
                    Confidence: {msg.confidence}%
                  </span>
                )}
              </div>

              {/* Agent Thinking process block */}
              {msg.thinkingSteps && msg.thinkingSteps.length > 0 && (
                <details className="group border-l-2 border-white/5 pl-4 mt-2">
                  <summary className="text-xs font-semibold text-muted-foreground hover:text-foreground cursor-pointer list-none flex items-center gap-1">
                    <Sparkles className="h-3 w-3 text-cyan-400" />
                    <span>View Search Reasoning Steps</span>
                    <ChevronRight className="h-3 w-3 transition-transform group-open:rotate-90" />
                  </summary>
                  <div className="mt-2 space-y-1.5 text-xs text-muted-foreground">
                    {msg.thinkingSteps.map((step, sIdx) => (
                      <div key={sIdx} className="flex gap-2 items-center">
                        <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0" />
                        <span>{step}</span>
                      </div>
                    ))}
                  </div>
                </details>
              )}

              {/* Content body */}
              <p className="text-sm leading-relaxed text-white whitespace-pre-wrap mt-2">{msg.text}</p>

              {/* Citations Card */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-4 border-t border-white/5 pt-4 space-y-3">
                  <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Retrieved References</h4>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {msg.sources.map((src) => (
                      <div key={src.id} className="rounded-lg bg-white/5 border border-white/5 p-3 space-y-1.5 hover:border-primary/20 transition-all">
                        <div className="flex items-center gap-2 text-xs">
                          {src.type === 'act' ? <BookOpen className="h-3 w-3 text-primary" /> : <Scale className="h-3 w-3 text-cyan-400" />}
                          <span className="font-bold text-white">{src.act} {src.section ? `(${src.section})` : ''}</span>
                        </div>
                        <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">{src.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action buttons */}
              {msg.sender === 'assistant' && (
                <div className="flex items-center gap-2 mt-4 border-t border-white/5 pt-3">
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-white" onClick={() => handleCopy(msg.text)}>
                    <Copy className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-white" onClick={() => {}}>
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-white" onClick={() => simulateStreamingResponse(msg.text)}>
                    <RotateCcw className="h-3.5 w-3.5" />
                  </Button>
                </div>
              )}
            </div>
          ))}

          {/* STREAMING ACTIVE STATE */}
          {agentStatus !== 'idle' && (
            <div className="flex flex-col gap-3 rounded-2xl p-5 border border-white/5 bg-card/30 w-full glass-panel">
              <div className="flex items-center gap-2">
                <div className="animate-pulse rounded-md p-1 bg-primary/20 text-primary">
                  <Brain className="h-4 w-4" />
                </div>
                <span className="text-xs font-bold text-muted-foreground">Generating advisory report...</span>
              </div>

              {agentStatus !== 'complete' && (
                <div className="mt-2 space-y-2 rounded-lg bg-white/5 border border-white/5 p-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-3 w-3 animate-spin text-primary" />
                    <span className="font-semibold text-white">Active pipeline state: {agentStatus.toUpperCase()}</span>
                  </div>
                </div>
              )}

              {streamingText && (
                <p className="text-sm leading-relaxed text-white whitespace-pre-wrap mt-2">
                  {streamingText}
                  <span className="inline-block h-3.5 w-1.5 bg-primary ml-1 animate-pulse"></span>
                </p>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* INPUT BAR BOX */}
      <div className="border-t border-white/5 bg-card/20 p-4">
        <div className="mx-auto max-w-3xl">
          <form
            onSubmit={(e) => { e.preventDefault(); handleSendQuery(input); }}
            className="relative flex items-center rounded-xl border border-white/5 bg-muted/40 p-2 shadow-inner"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={agentStatus !== 'idle'}
              placeholder={`Query LexOrch-KG via ${activeModel.toUpperCase()}...`}
              className="flex-1 bg-transparent px-4 py-2 text-sm text-white placeholder-muted-foreground focus:outline-none"
            />
            
            {agentStatus !== 'idle' ? (
              <Button
                type="button"
                onClick={() => setAgentStatus('idle')}
                className="bg-red-500 hover:bg-red-600 text-white rounded-lg p-2 h-9 w-9"
              >
                <StopCircle className="h-4.5 w-4.5" />
              </Button>
            ) : (
              <Button
                type="submit"
                disabled={!input.trim()}
                className="bg-primary text-primary-foreground hover:bg-primary/95 rounded-lg p-2 h-9 w-9"
              >
                <Send className="h-4.5 w-4.5" />
              </Button>
            )}
          </form>
          <div className="mt-2 text-center text-[10px] text-muted-foreground">
            LexOrch-KG processes arguments through hybrid search before generating recommendations. Output is for research purposes.
          </div>
        </div>
      </div>
    </div>
  );
}
