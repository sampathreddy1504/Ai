import React, { useState, useRef, useEffect } from "react";
import "bootstrap/dist/css/bootstrap.min.css";
import * as chrono from "chrono-node";
import SpeechToText from "./components/SpeechToText";

// 🟩 Backend URL (Render)
const API_BASE_URL = "https://ai-1-8ayp.onrender.com"; // your deployed backend

function Chatbox() {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [showFiles, setShowFiles] = useState(false);
  const [chatId, setChatId] = useState(() => localStorage.getItem("chat_id")); // ✅ persistent chat
  const chatContainerRef = useRef(null);

  // ✅ Scroll to bottom on new message
  useEffect(() => {
    chatContainerRef.current?.scrollTo({
      top: chatContainerRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  // ✅ Auto-load chat history if chat_id exists (optional, if backend supports)
  useEffect(() => {
    const loadHistory = async () => {
      if (!chatId) return;
      try {
        const res = await fetch(`${API_BASE_URL}/get-chat-history/${chatId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.messages) setMessages(data.messages);
        }
      } catch (err) {
        console.error("Error loading chat history:", err);
      }
    };
    loadHistory();
  }, [chatId]);

  // 🟩 Handle file selection
  const handleFileChange = (event) => {
    setSelectedFiles(Array.from(event.target.files));
    setShowFiles(true);
  };

  // 🟩 Main send function
  const handleSend = async () => {
    if (!userInput.trim() && selectedFiles.length === 0) return;

    const newUserMessage = {
      role: "user",
      content: userInput || "Uploaded files",
      files: selectedFiles,
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setUserInput("");
    setLoading(true);

    try {
      let response;

      // 🟢 If user uploaded files
      if (selectedFiles.length > 0) {
        const formData = new FormData();
        formData.append("file", selectedFiles[0]);
        formData.append(
          "prompt",
          JSON.stringify({ text: userInput || "Analyze the uploaded file" })
        );
        formData.append("token", localStorage.getItem("authToken") || "");
        formData.append("chat_id", chatId || null); // ✅ reuse chat id

        response = await fetch(`${API_BASE_URL}/chat-with-upload/`, {
          method: "POST",
          body: formData,
        });
      } else {
        // 🟢 Normal text chat request
        response = await fetch(`${API_BASE_URL}/chat/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_message: userInput,
            token: localStorage.getItem("authToken") || "",
            chat_id: chatId || null, // ✅ persist same chat
          }),
        });
      }

      const data = await response.json();

      const reply =
        data.reply ||
        data.response ||
        data.message ||
        "⚠️ No response received from AI.";

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: reply },
      ]);

      // ✅ If backend returns new chat_id, save it permanently
      if (data.chat_id && !chatId) {
        setChatId(data.chat_id);
        localStorage.setItem("chat_id", data.chat_id);
      }
    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `⚠️ Error: ${error.message}` },
      ]);
    } finally {
      setSelectedFiles([]);
      setShowFiles(false);
      setLoading(false);
    }
  };

  // 🎙 Handle speech-to-text input
  const handleSpeechResult = (text) => {
    setUserInput(text);
  };

  // 🔄 Start a new chat manually
  const startNewChat = () => {
    localStorage.removeItem("chat_id");
    setChatId(null);
    setMessages([]);
  };

  return (
    <div className="container py-3">
      {/* 🆕 New Chat Button */}
      <div className="d-flex justify-content-between align-items-center mb-2">
        <h4 className="fw-bold">💬 Personal AI Assistant</h4>
        <button className="btn btn-secondary btn-sm" onClick={startNewChat}>
          🆕 New Chat
        </button>
      </div>

      {/* Chat Window */}
      <div
        ref={chatContainerRef}
        className="chat-container border rounded p-3 mb-3"
        style={{
          height: "70vh",
          overflowY: "auto",
          background: "#f9f9f9",
        }}
      >
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`d-flex mb-3 ${
              msg.role === "user"
                ? "justify-content-end"
                : "justify-content-start"
            }`}
          >
            <div
              className={`p-2 rounded ${
                msg.role === "user"
                  ? "bg-primary text-white"
                  : "bg-light border text-dark"
              }`}
              style={{ maxWidth: "75%" }}
            >
              {msg.content}
              {msg.files &&
                msg.files.map((file, i) => (
                  <div key={i} className="mt-1 small text-warning">
                    📎 {file.name}
                  </div>
                ))}
            </div>
          </div>
        ))}
        {loading && (
          <div className="text-center text-secondary">AI is thinking...</div>
        )}
      </div>

      {/* File Upload Section */}
      <div className="mb-2">
        <input
          type="file"
          multiple
          onChange={handleFileChange}
          className="form-control"
        />
        {showFiles &&
          selectedFiles.map((f, i) => (
            <div key={i} className="small text-muted">
              📂 {f.name}
            </div>
          ))}
      </div>

      {/* Input & Buttons */}
      <div className="input-group">
        <input
          type="text"
          className="form-control"
          placeholder="Type your message..."
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />
        <button
          className="btn btn-primary"
          onClick={handleSend}
          disabled={loading}
        >
          Send
        </button>
        <SpeechToText onResult={handleSpeechResult} />
      </div>
    </div>
  );
}

export default Chatbox;
