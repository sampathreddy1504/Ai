import React, { useState, useRef, useEffect } from "react";
import { useTheme } from "./components/ThemeContext";
import "bootstrap/dist/css/bootstrap.min.css";
import * as chrono from "chrono-node";
import SpeechToText from "./components/SpeechToText";
import "../styles/ChatboxEnhanced.css";

export default function Chatbox({ chat }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [currentChatId, setCurrentChatId] = useState(null);
  const { theme, setTheme } = useTheme();
  const chatBodyRef = useRef(null);
  const fileInputRef = useRef(null);
  const typingIntervalRef = useRef(null); // holds timeout/interval id
  const typingSessionRef = useRef(0);

  // Initialize chat session (persist across navigation) — run once on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem("chatTheme") || "light";
    setTheme(savedTheme);

    const savedChatId = localStorage.getItem("chatId");
    const savedMessagesStr = localStorage.getItem("chatMessages");
    const savedMessages = savedMessagesStr ? JSON.parse(savedMessagesStr) : null;

    if (chat && chat.id) {
      // Continuing an existing conversation (opened from History)
      setCurrentChatId(chat.id);
      setMessages(chat.messages || []);
      localStorage.setItem("chatId", chat.id);
      localStorage.setItem("chatMessages", JSON.stringify(chat.messages || []));
    } else if (savedChatId) {
      // Restore ongoing chat - use saved id + messages (even if empty)
      setCurrentChatId(savedChatId);
      setMessages(savedMessages || []);
    } else if (savedMessages && Array.isArray(savedMessages) && savedMessages.length > 0) {
      // If messages exist but no explicit chatId key (edge case), try to recover a chat id
      try {
        const archiveRaw = localStorage.getItem("chatSessions") || "{}";
        const archive = JSON.parse(archiveRaw);
        const ids = Object.keys(archive);
        if (ids.length) {
          const lastId = ids[ids.length - 1];
          setCurrentChatId(lastId);
        } else {
          // Generate an id but treat this as a restored session (do not force "new chat" UX)
          const recoveredId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
          setCurrentChatId(recoveredId);
          localStorage.setItem("chatId", recoveredId);
        }
      } catch {
        const recoveredId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        setCurrentChatId(recoveredId);
        localStorage.setItem("chatId", recoveredId);
      }
      setMessages(savedMessages || []);
    } else {
      // No explicit saved chat id or messages. Try to recover the last archived chat (chatSessions)
      try {
        const archiveRaw = localStorage.getItem("chatSessions") || "{}";
        const archive = JSON.parse(archiveRaw);
        const ids = Object.keys(archive);
        if (ids.length) {
          const lastId = ids[ids.length - 1];
          const lastMsgs = Array.isArray(archive[lastId]) ? archive[lastId] : [];
          setCurrentChatId(lastId);
          setMessages(lastMsgs);
          localStorage.setItem("chatId", lastId);
          localStorage.setItem("chatMessages", JSON.stringify(lastMsgs));
        } else {
          // No archived chats either — create new chat id and empty messages
          const newId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
          setCurrentChatId(newId);
          setMessages([]);
          localStorage.setItem("chatId", newId);
          localStorage.setItem("chatMessages", JSON.stringify([]));
        }
      } catch {
        const newId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        setCurrentChatId(newId);
        setMessages([]);
        localStorage.setItem("chatId", newId);
        localStorage.setItem("chatMessages", JSON.stringify([]));
      }
    }

    // Try to fetch a personalized greeting from backend for first-open
    (async function fetchGreeting(){
      try {
        // Only fetch greeting if we haven't shown it in this browser session
        const greetedLocal = localStorage.getItem('greeted_local');
        if (greetedLocal) return;
        const token = localStorage.getItem('authToken');
        const params = new URLSearchParams();
        if (token) params.append('token', token);
        if (savedChatId) params.append('chat_id', savedChatId);
        const res = await fetch('/chat/greet?' + params.toString());
        if (!res.ok) return;
        const j = await res.json();
        if (j && j.message) {
          // Only insert greeting if messages array is currently empty
          setMessages((prev) => {
            if (prev && prev.length) return prev;
            return [
              {
                sender: 'bot',
                content: j.message,
                type: 'text',
                timestamp: new Date().toLocaleTimeString(),
              },
            ];
          });
          // mark locally so we don't fetch again this session
          try { localStorage.setItem('greeted_local', '1'); } catch {}
        }
        else {
          // If backend didn't return a message, try local user data stored on login
          try {
            const userRaw = localStorage.getItem('user');
            if (userRaw) {
              const u = JSON.parse(userRaw);
              const name = u?.name;
              if (name) {
                setMessages((prev) => {
                  if (prev && prev.length) return prev;
                  return [
                    {
                      sender: 'bot',
                      content: `Hello ${name}! How can I assist you today?`,
                      type: 'text',
                      timestamp: new Date().toLocaleTimeString(),
                    },
                  ];
                });
                try { localStorage.setItem('greeted_local', '1'); } catch {}
              }
            }
          } catch {}
        }
      } catch (e) {
        // ignore failures
      }
    })();
  }, []);

  // If a `chat` prop is later provided (e.g., user opened a chat from History), update UI
  useEffect(() => {
    if (chat && chat.id) {
      setCurrentChatId(chat.id);
      setMessages(chat.messages || []);
      try {
        localStorage.setItem("chatId", chat.id);
        localStorage.setItem("chatMessages", JSON.stringify(chat.messages || []));
      } catch {}
    }
  }, [chat]);

  // Persist chat + theme
  useEffect(() => {
    if (currentChatId) localStorage.setItem("chatId", currentChatId);
    localStorage.setItem("chatMessages", JSON.stringify(messages));
    localStorage.setItem("chatTheme", theme);
  }, [messages, currentChatId, theme]);

  // Smooth scroll to bottom
  const scrollToBottom = () => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTo({
        top: chatBodyRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  };
  useEffect(scrollToBottom, [messages]);

  // Typing simulation (word-by-word) with de-dupe and single temp bubble
  const simulateTyping = (fullText) => {
    // Stop any previous typing interval
    if (typingIntervalRef.current) {
      clearInterval(typingIntervalRef.current);
      typingIntervalRef.current = null;
    }

    // Start a new typing session (guards against duplicate intervals)
    typingSessionRef.current += 1;
    const sessionId = typingSessionRef.current;

    const tokens = fullText.match(/\S+\s*/g) || [fullText]; // words with trailing spaces
    let index = 0;
    setIsTyping(true);
    // Ensure a single temp message exists and is empty
    setMessages((prev) => {
      // Remove any existing temp
      let next = prev.filter((m) => m.sender !== "bot-temp");
      // If the last message is already the same final bot content, remove it to avoid duplicate during typing
      if (next.length && next[next.length - 1].sender === "bot" && next[next.length - 1].content === fullText) {
        next = next.slice(0, -1);
      }
      return [
        ...next,
        {
          sender: "bot-temp",
          content: "",
          type: "text",
          timestamp: new Date().toLocaleTimeString(),
        },
      ];
    });

    const step = () => {
      // Abort if a new typing session started
      if (typingSessionRef.current !== sessionId) return;
      if (index < tokens.length) {
        const displayed = tokens.slice(0, index + 1).join("");
        setMessages((prev) => {
          const temp = [...prev];
          if (temp[temp.length - 1]?.sender === "bot-temp") {
            temp[temp.length - 1].content = displayed;
          }
          return temp;
        });
        index++;
        typingIntervalRef.current = setTimeout(step, 120);
      } else {
        setIsTyping(false);
        setMessages((prev) => {
          const filtered = prev.filter((m) => m.sender !== "bot-temp");
          // Avoid pushing duplicate final message
          if (filtered.length && filtered[filtered.length - 1].sender === "bot" && filtered[filtered.length - 1].content === fullText) {
            return filtered;
          }
          filtered.push({
            sender: "bot",
            content: fullText,
            type: "text",
            timestamp: new Date().toLocaleTimeString(),
          });
          return filtered;
        });
        typingIntervalRef.current = null;
      }
    };
    typingIntervalRef.current = setTimeout(step, 120);
  };

  // Cleanup on unmount to avoid stray intervals
  useEffect(() => {
    return () => {
      if (typingIntervalRef.current) {
        clearTimeout(typingIntervalRef.current);
        typingIntervalRef.current = null;
      }
      typingSessionRef.current += 1; // invalidate any running session
    };
  }, []);

  // Send message (unchanged)
  const sendMessage = async () => {
    if (!input.trim()) return;
    const newMsg = {
      sender: "user",
      content: input,
      type: "text",
      timestamp: new Date().toLocaleTimeString(),
    };
    setMessages((prev) => [...prev, newMsg]);
    setInput("");
    setIsTyping(true);

    try {
      const token = localStorage.getItem("authToken");
      const userRaw = localStorage.getItem('user');
      const userObj = userRaw ? JSON.parse(userRaw) : null;
      const res = await fetch("/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_message: input,
          token,
          chat_id: currentChatId,
          user_name: userObj?.name,
          user_email: userObj?.email,
        }),
      });
      const data = await res.json();
      const reply = data.reply || data.response || "⚠ No AI response";
      simulateTyping(reply);
      // adopt canonical chat id if backend returns it
      if (data.chat_id && data.chat_id !== currentChatId) {
        setCurrentChatId(data.chat_id);
        localStorage.setItem("chatId", data.chat_id);
      }
      // open external URL if provided
      if (data.open_url) {
        try {
          const urlStr = String(data.open_url);
          if (urlStr.includes("youtube.com/results?search_query=")) {
            // Resolve top YouTube video and open watch URL with autoplay
            const q = decodeURIComponent(urlStr.split("search_query=")[1] || "");
            try {
              const api = `https://piped.video/api/v1/search?q=${encodeURIComponent(q)}&region=IN`;
              const r = await fetch(api, { headers: { "Accept": "application/json" } });
              const j = await r.json();
              const item = Array.isArray(j) ? j.find(x => (x.type === "video" || x.duration) && (x.url || x.id)) : null;
              let vid = item?.id || "";
              if (!vid && item?.url) {
                const m = String(item.url).match(/v=([^&]+)/);
                if (m) vid = m[1];
              }
              if (vid) {
                const watchUrl = `https://www.youtube.com/watch?v=${vid}&autoplay=1&mute=1`;
                window.open(watchUrl, "_blank", "noopener,noreferrer");
              } else {
                window.open(urlStr, "_blank", "noopener,noreferrer");
              }
            } catch {
              window.open(urlStr, "_blank", "noopener,noreferrer");
            }
          } else {
            window.open(urlStr, "_blank", "noopener,noreferrer");
          }
        } catch {}
      }
      // if backend returns a canonical chat_id (e.g., UUID), adopt it
      if (data.chat_id && data.chat_id !== currentChatId) {
        setCurrentChatId(data.chat_id);
      }
    } catch {
      setIsTyping(false);
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          content: "⚠ Unable to reach backend",
          type: "text",
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
    }
  };

  // File upload (unchanged)
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const previewURL = URL.createObjectURL(file);
    setMessages((prev) => [
      ...prev,
      {
        sender: "user",
        content: previewURL,
        type: "image",
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
    scrollToBottom();

    const formData = new FormData();
    formData.append("file", file);
    formData.append("token", localStorage.getItem("authToken"));
    formData.append("chat_id", currentChatId);

    try {
      const res = await fetch("/chat-with-upload/", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      const reply = data.response || "⚠ File processed, no detailed reply.";
      simulateTyping(reply);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          content: "⚠ File upload failed",
          type: "text",
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
    }
  };

  // Extra actions

  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };

  const startNewChat = () => {
    // Preserve current thread's messages in a simple local archive
    try {
      const archiveRaw = localStorage.getItem("chatSessions") || "{}";
      const archive = JSON.parse(archiveRaw);
      if (currentChatId && Array.isArray(messages) && messages.length) {
        archive[currentChatId] = messages;
        localStorage.setItem("chatSessions", JSON.stringify(archive));
      }
    } catch {}

    const newId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setCurrentChatId(newId);
    setMessages([]);
    localStorage.setItem("chatId", newId);
    localStorage.setItem("chatMessages", JSON.stringify([]));
  };

  // ----- Dev debug panel (visible when localStorage.debug === '1') -----
  const [debugOn, setDebugOn] = useState(Boolean(localStorage.getItem('debug')));
  const [debugState, setDebugState] = useState({});
  const refreshDebug = () => {
    try {
      const token = localStorage.getItem('authToken');
      const userRaw = localStorage.getItem('user');
      const userObj = userRaw ? JSON.parse(userRaw) : null;
      const chatIdLS = localStorage.getItem('chatId');
      const chatMsgsRaw = localStorage.getItem('chatMessages');
      const msgs = chatMsgsRaw ? JSON.parse(chatMsgsRaw) : null;
      const greeted = localStorage.getItem('greeted_local');
      setDebugState({ token: token ? (token.slice(0,20) + '...') : null, user: userObj, chatId: chatIdLS, messagesCount: Array.isArray(msgs) ? msgs.length : null, greeted });
    } catch {
      setDebugState({});
    }
  };

  useEffect(() => {
    if (debugOn) refreshDebug();
  }, [debugOn, messages, currentChatId]);

  

  return (
    <div className={`chat-wrapper ${theme}-theme`}>
      <div className="chatbox shadow-lg">
        {/* Header */}
        <div className="chat-header d-flex justify-content-between align-items-center">
          <div className="d-flex align-items-center gap-2">
            <h5 className="mb-0">💬 AI Chat Assistant</h5>
            <button
              className="theme-toggle-btn"
              onClick={toggleTheme}
              title="Toggle Theme"
            >
              {theme === "dark" ? "🌙" : "☀️"}
            </button>
          </div>

          <div className="d-flex gap-2">
            <button className="btn btn-sm btn-primary" onClick={startNewChat} title="Start New Chat">
              ✨ New Chat
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="chat-body" ref={chatBodyRef}>
          {messages.length === 0 ? (
            <div className="chat-placeholder">
              👋 Hello! Ask something to start chatting...
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`chat-message ${msg.sender}`}>
                {msg.type === "text" ? (
                  <div className="message-bubble">{msg.content}</div>
                ) : (
                  <img
                    src={msg.content}
                    alt="upload"
                    className="message-image"
                  />
                )}
                <small className="timestamp">{msg.timestamp}</small>
              </div>
            ))
          )}
          {isTyping && (
            <div className="chat-message bot">
              <div className="message-bubble typing-bubble">
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="chat-input-area">
          <div className="chat-extra-btns">
            <div
              className="extra-btn"
              onClick={() => fileInputRef.current.click()}
              title="Attach File"
            >
              📎
            </div>
            <SpeechToText onChange={setInput} />
          </div>

          <input
            type="file"
            ref={fileInputRef}
            style={{ display: "none" }}
            accept="image/*,.pdf,.txt,.doc,.docx"
            onChange={handleFileUpload}
          />

          <input
            type="text"
            className="chat-input"
            placeholder="Type a message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          />

          <button className="send-btn" onClick={sendMessage}>
            ➤
          </button>
        </div>
      </div>
      {/* Dev debug panel */}
      {debugOn && (
        <div style={{position: 'fixed', right: 12, bottom: 12, width: 320, maxHeight: '45vh', overflow: 'auto', background: 'rgba(0,0,0,0.8)', color: '#fff', padding: 12, borderRadius: 8, fontSize: 12, zIndex: 9999}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6}}>
            <strong>DEV DEBUG</strong>
            <div>
              <button className="btn btn-sm btn-light" onClick={() => { setDebugOn(false); localStorage.removeItem('debug'); }} style={{marginRight:6}}>Hide</button>
              <button className="btn btn-sm btn-secondary" onClick={refreshDebug}>Refresh</button>
            </div>
          </div>
          <div style={{whiteSpace:'pre-wrap'}}><strong>token:</strong> {debugState.token || '(none)'}</div>
          <div style={{whiteSpace:'pre-wrap'}}><strong>user:</strong> {debugState.user ? JSON.stringify(debugState.user) : '(none)'}</div>
          <div><strong>chatId:</strong> {debugState.chatId || '(none)'}</div>
          <div><strong>messagesCount:</strong> {debugState.messagesCount ?? '(none)'}</div>
          <div><strong>greeted_local:</strong> {debugState.greeted ?? '(none)'}</div>
        </div>
      )}
    </div>
  );
}
