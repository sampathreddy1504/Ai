import React, { useState } from "react";
import axios from "axios";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  const handleLogin = async () => {
    if (!email || !password) {
      setMessage("⚠️ Please enter email and password");
      return;
    }

    try {
      const res = await axios.post("/auth/login", { email, password });
      setMessage(res.data.message);

      if (res.data.success && res.data.token && res.data.user) {
        localStorage.setItem("authToken", res.data.token);
        localStorage.setItem("user", JSON.stringify(res.data.user));
        // Ensure chatId is restored from any archived sessions so reload continues previous chat
        try {
          let chatId = localStorage.getItem("chatId");
          if (!chatId) {
            const archiveRaw = localStorage.getItem("chatSessions") || "{}";
            const archive = JSON.parse(archiveRaw);
            const ids = Object.keys(archive);
            if (ids.length) {
              const lastId = ids[ids.length - 1];
              localStorage.setItem("chatId", lastId);
              localStorage.setItem("chatMessages", JSON.stringify(archive[lastId] || []));
            } else {
              // if no archive, but chatMessages exists, keep them under a recovered id
              const msgRaw = localStorage.getItem("chatMessages");
              const msgs = msgRaw ? JSON.parse(msgRaw) : null;
              if (msgs && Array.isArray(msgs) && msgs.length) {
                const recoveredId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
                localStorage.setItem("chatId", recoveredId);
                localStorage.setItem("chatMessages", JSON.stringify(msgs));
              }
            }
          }
        } catch {}

        setTimeout(() => {
          window.location.href = "/chat";
        }, 500);
      } else {
        setMessage("Login failed");
      }
    } catch (error) {
      setMessage(error.response?.data?.message || "Login failed");
    }
  };

  return (
    <div
      className="d-flex align-items-center justify-content-center vh-100"
      style={{ background: "linear-gradient(135deg, #6f42c1, #0d6efd)" }}
    >
      <div
        className="card shadow-lg border-0 rounded-4 p-4 p-md-5"
        style={{ maxWidth: "400px", width: "100%" }}
      >
        {/* Header */}
        <div className="text-center mb-4">
          <h2 className="fw-bold mb-2">Welcome Back!</h2>
          <p className="text-muted mb-0">Sign in to your account</p>
        </div>

        {/* Form */}
        <div className="mb-3">
          <label className="form-label fw-semibold">Email Address</label>
          <input
            type="email"
            className="form-control form-control-sm"
            placeholder="Enter your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div className="mb-4">
          <label className="form-label fw-semibold">Password</label>
          <input
            type="password"
            className="form-control form-control-sm"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <button
          className="btn btn-primary w-100 fw-bold py-2 mb-3"
          onClick={handleLogin}
        >
          Login
        </button>

        <div className="text-center">
          <p className="small mb-0">
            Don’t have an account?{" "}
            <a
              href="/signup"
              className="text-primary fw-semibold text-decoration-none"
            >
              Sign Up
            </a>
          </p>
        </div>

        {message && (
          <div className="alert alert-info mt-3 text-center py-2 mb-0">
            {message}
          </div>
        )}
      </div>
    </div>
  );
}

export default Login;
