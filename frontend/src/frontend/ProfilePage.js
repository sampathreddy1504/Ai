import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTheme } from "./components/ThemeContext";
import "../styles/Profile.css";

export default function ProfilePage() {
  const [user, setUser] = useState({ name: null, email: null });
  const [confirmOpen, setConfirmOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    try {
      const raw = localStorage.getItem("user");
      if (raw) setUser(JSON.parse(raw));
    } catch (e) {
      // ignore
    }
  }, []);

  const handleSignOut = () => setConfirmOpen(true);
  const cancel = () => setConfirmOpen(false);
  const confirm = () => {
    localStorage.removeItem("authToken");
    localStorage.removeItem("user");
    setConfirmOpen(false);
    navigate("/login");
  };

  const { theme } = useTheme();

  return (
    <div className={`profile-page container py-4 ${theme === 'dark' ? 'theme-dark' : 'theme-light'}`}>
      <div className="card mx-auto profile-card" style={{ maxWidth: 600 }}>
        <div className="card-body">
          <h4 className="card-title">Profile</h4>
          <p className="text-muted">Your account information</p>

          <div className="mb-3">
            <label className="form-label">Name</label>
            <div className="p-2 border rounded">{user.name || "(not provided)"}</div>
          </div>

          <div className="mb-3">
            <label className="form-label">Email</label>
            <div className="p-2 border rounded">{user.email || "(not provided)"}</div>
          </div>

          <div className="d-flex justify-content-end">
            <button className="btn btn-outline-danger" onClick={handleSignOut}>
              Sign Out
            </button>
          </div>
        </div>
      </div>

      {confirmOpen && (
        <div className="profile-confirm-overlay">
          <div className="profile-confirm-card card p-3">
            <h5>Confirm Sign Out</h5>
            <p>Are you sure you want to sign out?</p>
            <div className="d-flex justify-content-end gap-2">
              <button className="btn btn-secondary" onClick={cancel}>
                Cancel
              </button>
              <button className="btn btn-danger" onClick={confirm}>
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
