import React, { useState, useEffect } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import "bootstrap/dist/css/bootstrap.min.css";
import { Modal, Button } from "react-bootstrap";
import axios from "axios";

function History() {
  const [history, setHistory] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { onContinueChat } = useOutletContext() || {};

  useEffect(() => {
    loadChatHistory();
  }, []);

  const loadChatHistory = async () => {
    try {
      const token = localStorage.getItem("authToken");
      if (!token) {
        navigate("/login");
        return;
      }

      const response = await axios.get("/api/conversations", {
        params: { token }
      });

      if (response.data.success) {
        // Transform the backend data to match the expected frontend format
        const conversations = response.data.conversations.map(conv => ({
          id: conv.chat_id,
          title: conv.title,
          messages: [] // Will be loaded when selected
        }));
        setHistory(conversations);
      }
    } catch (error) {
      console.error("Failed to load chat history:", error);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  const deleteChat = async (id) => {
    try {
      const token = localStorage.getItem("authToken");
      if (!token) return;

      // TODO: Add delete endpoint to backend if needed
      // For now, just remove from local state
      const updatedHistory = history.filter((session) => session.id !== id);
      setHistory(updatedHistory);
      setShowModal(false);

      if (selectedChat?.id === id) {
        setSelectedChat(null);
      }
    } catch (error) {
      console.error("Failed to delete chat:", error);
    }
  };

  const handleChatClick = async (chat) => {
    try {
      const token = localStorage.getItem("authToken");
      if (!token) return;

      // Load messages for this chat
      const response = await axios.get(`/api/conversations/${chat.id}`, {
        params: { token }
      });

      if (response.data.success) {
        const chatWithMessages = {
          ...chat,
          messages: response.data.messages
        };
        setSelectedChat(chatWithMessages);
        setShowModal(true);
      }
    } catch (error) {
      console.error("Failed to load chat messages:", error);
      setSelectedChat(chat);
      setShowModal(true);
    }
  };

  const continueChat = () => {
    if (!selectedChat) return;
    // Persist the selected thread into localStorage so Chatbox restores it
    try {
      localStorage.setItem("chatId", selectedChat.id);
      localStorage.setItem("chatMessages", JSON.stringify(selectedChat.messages || []));
    } catch {}

    if (onContinueChat) {
      onContinueChat(selectedChat);
    }
    setShowModal(false);
    navigate("/chat");
  };

  return (
    <div className="container-fluid vh-100" style={{ height: "100vh", minHeight: 0 }}>
      <div className="row h-100" style={{ minHeight: 0 }}>
        {/* Sidebar */}
        <div className="col-3 col-md-2 border-end p-0 d-flex flex-column" style={{ height: "100vh", minHeight: 0 }}>
          <div className="p-3 border-bottom fw-bold">Chat History</div>
          <div className="list-group list-group-flush flex-grow-1 overflow-auto" style={{ minHeight: 0 }}>
            {loading ? (
              <div className="p-3 text-muted small">Loading...</div>
            ) : history.length > 0 ? (
              history.map((session) => (
                <button
                  key={session.id}
                  className="list-group-item list-group-item-action text-start"
                  onClick={() => handleChatClick(session)}
                >
                  {session.title.length > 25
                    ? session.title.slice(0, 25) + "..."
                    : session.title}
                </button>
              ))
            ) : (
              <div className="p-3 text-muted small">No chat history yet</div>
            )}
          </div>
        </div>

        {/* Main Chat Display */}
        <div className="col-9 col-md-10 d-flex flex-column" style={{ height: "100vh", minHeight: 0 }}>
          <div className="p-3 border-bottom bg-white fw-bold">
            {selectedChat ? selectedChat.title : "Select a chat"}
          </div>

          <div className="flex-grow-1 p-3 overflow-auto">
            {selectedChat ? (
              selectedChat.messages.map((msg, i) => (
                <div
                  key={i}
                  className={`d-flex mb-2 ${
                    msg.sender === "user"
                      ? "justify-content-end"
                      : "justify-content-start"
                  }`}
                >
                  <div
                    className={`p-2 px-3 rounded-3 shadow-sm ${
                      msg.sender === "user"
                        ? "bg-primary text-white"
                        : "bg-white"
                    }`}
                    style={{ maxWidth: "70%" }}
                  >
                    {msg.content}
                  </div>
                </div>
              ))
            ) : (
              <div className="h-100 d-flex align-items-center justify-content-center text-muted">
                <p className="text-center">
                  👈 Select a chat from the left to view messages
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bootstrap Modal */}
      <Modal show={showModal} onHide={() => setShowModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>{selectedChat?.title}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <p>Do you want to continue this chat or delete it from history?</p>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={() => deleteChat(selectedChat.id)}>
            Delete
          </Button>
          <Button variant="success" onClick={continueChat}>
            Continue Chat
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default History;
