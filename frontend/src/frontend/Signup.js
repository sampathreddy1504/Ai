import React, { useState, useEffect } from "react";
import axios from "axios";

function Signup() {
  const [step, setStep] = useState("form"); // form | otp (otp disabled after JWT auth)
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [message, setMessage] = useState("");
  const [timer, setTimer] = useState(30);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let interval = null;
    if (step === "otp" && timer > 0) {
      interval = setInterval(() => setTimer((prev) => prev - 1), 1000);
    } else if (timer === 0) {
      clearInterval(interval);
      setMessage("⚠️ OTP expired. Please resend OTP.");
    }
    return () => clearInterval(interval);
  }, [step, timer]);

  const handleSignup = async () => {
    if (!name || !email || !password) {
      setMessage("⚠️ Please fill all fields");
      return;
    }
    setLoading(true);
    setMessage("⏳ Creating account...");
    try {
      const res = await axios.post("/auth/signup", { name, email, password });
      if (res.data.success && res.data.token && res.data.user) {
        localStorage.setItem("authToken", res.data.token);
        localStorage.setItem("user", JSON.stringify(res.data.user));
        setMessage("✅ Account created! Redirecting...");
        // Restore last chat session if any so reload continues previous chat
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

        setTimeout(() => (window.location.href = "/chat"), 500);
      } else {
        setMessage(res.data.message || "Signup failed");
      }
    } catch (err) {
      setMessage(err.response?.data?.message || "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    // OTP flow disabled; using immediate JWT signup
    setMessage("⚠️ OTP flow is disabled.");
  };

  const handleResendOtp = async () => {
    setMessage("⚠️ OTP flow is disabled.");
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
          <div
            className="d-inline-flex align-items-center justify-content-center rounded-circle mb-3"
            style={{ width: "60px", height: "60px", background: "#fff" }}
          >
            <i
              className={`bi ${
                step === "form" ? "bi-person-plus-fill" : "bi-key-fill"
              } fs-4 text-primary`}
            ></i>
          </div>
          <h2 className="fw-bold mb-2">
            {step === "form" ? "Create Account" : "Verify"}
          </h2>
          <p className="text-muted mb-0">
            {step === "form"
              ? "Sign up with your details"
              : "Immediate signup used; OTP disabled"}
          </p>
        </div>

        {/* Form Step */}
        {step === "form" && (
          <>
            <div className="mb-3">
              <label className="form-label fw-semibold">Full Name</label>
              <input
                type="text"
                className="form-control"
                placeholder="Enter your name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="mb-3">
              <label className="form-label fw-semibold">Email</label>
              <input
                type="email"
                className="form-control"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div className="mb-4">
              <label className="form-label fw-semibold">Password</label>
              <input
                type="password"
                className="form-control"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button
              className="btn btn-success w-100 fw-bold py-2"
              onClick={handleSignup}
              disabled={loading}
            >
              {loading ? "⏳ Creating Account..." : "Create Account"}
            </button>
          </>
        )}

        {/* OTP Step */}
        {step === "otp" && (
          <>
            <div className="mb-3">
              <label className="form-label fw-semibold">Enter OTP</label>
              <input
                type="text"
                className="form-control"
                placeholder="Enter OTP"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
              />
            </div>

            <button
              className="btn btn-primary w-100 mb-2 fw-bold py-2"
              onClick={handleVerifyOtp}
            >
              Verify OTP
            </button>

            <div className="text-center text-muted small">
              OTP expires in: <strong>{timer}</strong> seconds
              {timer === 0 && (
                <button
                  className="btn btn-link ms-2 p-0"
                  onClick={handleResendOtp}
                >
                  Resend OTP
                </button>
              )}
            </div>
          </>
        )}

        {message && (
          <div className="alert alert-info mt-3 text-center">{message}</div>
        )}
      </div>
    </div>
  );
}

export default Signup;
