import React, { useEffect, useState } from "react";
import {
  Bot,
  Send,
  Sparkles,
  Database,
  RefreshCw,
} from "lucide-react";
import { api } from "../api";

interface Message {
  sender: "user" | "copilot";
  text: string;
  sources?: string[];
  engine?: string;
}

export const AiCopilotPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: "copilot",
      text: "Hello, Technician. I am your **Ghost-OS Offline Intelligence Copilot**. I have direct read-only access to the encrypted Ghost Vault SQLite database. I can explain hardware failures, trace degradation trends, interpret SMART registers, and verify component history—100% offline with zero cloud telemetry.",
      sources: ["Ghost Vault Knowledge Base"],
      engine: "Deterministic Fallback & Vault Inspector",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [aiStatus, setAiStatus] = useState<{
    is_gguf_active: boolean;
    model_name: string | null;
    fallback_engine: string;
  } | null>(null);

  useEffect(() => {
    api.getAiStatus().then(setAiStatus).catch(() => {});
  }, []);

  const handleSend = async (queryText?: string) => {
    const q = queryText || input;
    if (!q.trim() || loading) return;

    const userMsg: Message = { sender: "user", text: q };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.chatWithAi(q);
      const botMsg: Message = {
        sender: "copilot",
        text: res.reply,
        sources: res.sources,
        engine: res.engine_used === "llama_cpp" ? `GGUF (${res.model_name})` : "Deterministic Rules & SQL Synthesis",
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "copilot",
          text: `⚠️ Error querying Vault intelligence: ${err.message}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const quickPrompts = [
    "Summarize active warnings across the fleet",
    "Explain NVMe percentage_used and endurance thresholds",
    "What are the specs and health score of the latest machine?",
    "Detect any component changes or degradation alerts",
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner & Offline Engine Status */}
      <div className="bg-black border border-zinc-800 rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-red-600 via-red-500 to-red-600" />
        <div>
          <h1 className="text-xl font-black text-white flex items-center gap-2">
            <Bot className="w-5 h-5 text-red-500" />
            Ghost-AI Copilot
            <span className="text-xs px-2 py-0.5 rounded bg-red-950 border border-red-700 text-red-400 font-mono font-bold">
              100% OFFLINE
            </span>
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Grounded strictly in local decrypted SQLite telemetry. Zero hallucinations.
          </p>
        </div>

        {/* Engine Status Badge */}
        <div className="flex items-center gap-2 bg-zinc-950 border border-zinc-800 px-3.5 py-2 rounded-xl text-xs">
          <Sparkles className="w-4 h-4 text-red-500" />
          <span className="text-zinc-400">Inference Engine:</span>
          {aiStatus?.is_gguf_active ? (
            <span className="font-mono text-white font-bold">
              LLAMA.CPP ({aiStatus.model_name})
            </span>
          ) : (
            <span className="font-mono text-white font-bold">
              Deterministic Rules &amp; Vault SQL
            </span>
          )}
        </div>
      </div>

      {/* Chat Window */}
      <div className="bg-black border border-zinc-800 rounded-2xl h-[560px] flex flex-col overflow-hidden shadow-2xl">
        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex gap-3 max-w-3xl ${m.sender === "user" ? "ml-auto justify-end" : "mr-auto"}`}
            >
              {m.sender === "copilot" && (
                <div className="w-8 h-8 rounded-lg bg-red-950/80 border border-red-700/60 flex items-center justify-center shrink-0 text-red-500 mt-1 shadow-inner">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`p-4 rounded-2xl text-xs leading-relaxed space-y-2 ${
                  m.sender === "user"
                    ? "bg-red-600 text-white rounded-tr-none shadow-lg shadow-red-950/70 font-medium"
                    : "bg-zinc-950 border border-zinc-800 text-zinc-100 rounded-tl-none shadow-xl"
                }`}
              >
                <div className="whitespace-pre-line">{m.text}</div>

                {m.sources && m.sources.length > 0 && (
                  <div className="pt-2 border-t border-zinc-800 flex flex-wrap items-center gap-2 text-[10px] text-zinc-400">
                    <Database className="w-3 h-3 text-red-500" />
                    <span>Grounding Sources:</span>
                    {m.sources.map((s, sIdx) => (
                      <span
                        key={sIdx}
                        className="px-1.5 py-0.5 rounded bg-black border border-zinc-800 text-red-400 font-mono"
                      >
                        {s}
                      </span>
                    ))}
                    {m.engine && (
                      <span className="ml-auto text-zinc-500 font-mono">{m.engine}</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3 mr-auto items-center text-xs text-zinc-400 font-mono">
              <div className="w-8 h-8 rounded-lg bg-red-950/80 border border-red-700/60 flex items-center justify-center shrink-0 text-red-500">
                <RefreshCw className="w-4 h-4 animate-spin" />
              </div>
              <span>Querying decrypted Vault SQLite facts...</span>
            </div>
          )}
        </div>

        {/* Quick Suggestion Pills */}
        <div className="px-6 py-2.5 bg-zinc-950 border-t border-zinc-800/80 flex items-center gap-2 overflow-x-auto text-[11px]">
          <span className="text-zinc-500 shrink-0 font-medium">Quick Prompts:</span>
          {quickPrompts.map((p, i) => (
            <button
              key={i}
              onClick={() => handleSend(p)}
              disabled={loading}
              className="px-3 py-1 rounded-full bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white shrink-0 transition border border-zinc-700 cursor-pointer disabled:opacity-50"
            >
              {p}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="p-4 bg-zinc-950 border-t border-zinc-800 flex items-center gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder="Ask about machine health, component changes, SMART wear..."
            className="flex-1 px-4 py-2.5 rounded-xl bg-black border border-zinc-800 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-red-500 disabled:opacity-50 font-mono"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="p-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white transition disabled:opacity-50 shadow-lg shadow-red-950/70 cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
