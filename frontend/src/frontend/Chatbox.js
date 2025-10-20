import React, { useState, useRef, useEffect } from "react";
import "bootstrap/dist/css/bootstrap.min.css";
import * as chrono from "chrono-node";
import SpeechToText from "./components/SpeechToText";

// 🟩 Backend URL (Render)
const API_BASE_URL = "https://ai-1-wfwv.onrender.com"; // ← your backend Render URL

function Chatbox({ chat }) {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [showFiles, setShowFiles] = useState(false);
  const chatContainerRef = useRef(null);

  // Scroll to bottom on new message
  useEffect(() => {
    chatContainerRef.current?.scrollTo({
      top: chatContainerRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const handleFileChange = (event) => {
    setSelectedFiles(Array.from(event.target.files));
    setShowFiles(true);
  };

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

      // 🟩 If user uploaded files (docs/images)
      if (selectedFiles.length > 0) {
        const formData = new FormData();
        selectedFiles.forEach((file) => formData.append("files", file));
        formData.append("query", userInput || "Analyze the uploaded files");

        response = await fetch(`${API_BASE_URL}/chat-with-upload/`, {
          method: "POST",
          body: formData,
        });
      } else {
        // 🟩 Normal text query
        response = await fetch(`${API_BASE_URL}/chat/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: userInput }),
        });
      }

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response || "No response" },
      ]);
    } catch (error) {
      console.error("Error:", error);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ Failed to connect to backend." },
      ]);
    } finally {
      setSelectedFiles([]);
      setShowFiles(false);
      setLoading(false);
    }
  };

  const handleSpeechResult = (text) => {
    setUserInput(text);
  };

  return (
    <div className="container py-3">
      <div
        ref={chatContainerRef}
        className="chat-container border rounded p-3 mb-3"
        style={{ height: "70vh", overflowY: "auto", background: "#f9f9f9" }}
      >
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`d-flex mb-3 ${
              msg.role === "user" ? "justify-content-end" : "justify-content-start"
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

      {/* File Upload */}
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

      {/* Text Input */}
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
