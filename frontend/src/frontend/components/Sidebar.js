import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  FaComments,
  FaTasks,
  FaCalendarAlt,
  FaHistory,
  FaCog,
} from "react-icons/fa";
import ProfileIcon from "../ProfileIcon";
import "bootstrap/dist/css/bootstrap.min.css";
import "../../styles/Sidebar.css";

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  const links = [
    { path: "/chat", name: "Chat", icon: <FaComments /> },
    { path: "/tasks", name: "Tasks", icon: <FaTasks /> },
    { path: "/calendar", name: "Calendar", icon: <FaCalendarAlt /> },
    { path: "/history", name: "History", icon: <FaHistory /> },
    { path: "/settings", name: "Settings", icon: <FaCog /> },
  ];

  // handleSignOut removed (sidebar uses ProfileIcon navigation)

  const [showModal, setShowModal] = useState(false);
  const [userInfo, setUserInfo] = useState({ name: null, email: null });

  useEffect(() => {
    try {
      const raw = localStorage.getItem("user");
      if (raw) {
        const u = JSON.parse(raw);
        setUserInfo({ name: u.name || null, email: u.email || null });
      }
    } catch (e) {
      // ignore parse errors
    }
  }, []);

  const confirmSignOut = () => {
    localStorage.removeItem("authToken");
    localStorage.removeItem("user");
    setShowModal(false);
    navigate("/login");
  };

  const cancelSignOut = () => setShowModal(false);

  // Create a DOM node for the modal portal
  const [modalContainer] = useState(() => {
    if (typeof document !== "undefined") {
      const el = document.createElement("div");
      el.setAttribute("id", "sidebar-modal-root");
      return el;
    }
    return null;
  });

  useEffect(() => {
    if (!modalContainer) return;
    document.body.appendChild(modalContainer);
    return () => {
      document.body.removeChild(modalContainer);
    };
  }, [modalContainer]);

  return (
  <div className="sidebar-container d-flex flex-column p-3 shadow-lg vh-100">
      {/* Sidebar Header */}
      <h4 className="text-center mb-4 fw-bold text-info">MyAI Assistant</h4>

      {/* Navigation Links */}
      <ul className="nav flex-column flex-grow-1">
        {links.map((link) => (
          <li key={link.path} className="nav-item mb-2">
            <Link
              to={link.path}
              className={`nav-link d-flex align-items-center rounded py-2 px-3 ${
                location.pathname === link.path ? "active-link" : ""
              }`}
            >
              <span className="me-3 fs-5">{link.icon}</span>
              <span className="link-text">{link.name}</span>
            </Link>
          </li>
        ))}
      </ul>

      {/* Profile icon/link (navigates to profile page) */}
      <div className="mt-auto">
        <ProfileIcon name={userInfo.name} />
      </div>

      {/* Profile modal (shows profile details and sign out placed at last) */}
      {showModal &&
        modalContainer &&
        ReactDOM.createPortal(
          <div className="sidebar-modal-overlay">
            <div className="sidebar-modal card p-3">
              <div className="d-flex justify-content-between align-items-start mb-2">
                <h5 className="mb-0">Profile</h5>
                <button className="btn btn-sm btn-secondary" onClick={cancelSignOut}>Close</button>
              </div>

              <div className="mb-3">
                <p className="mb-1"><strong>Name:</strong> {userInfo.name || "(not available)"}</p>
                <p className="mb-0"><strong>Email:</strong> {userInfo.email || "(not available)"}</p>
              </div>

              <div className="mt-4 d-flex justify-content-end">
                <button className="btn btn-danger" onClick={confirmSignOut}>Sign Out</button>
              </div>
            </div>
          </div>,
          modalContainer
        )}
    </div>
  );
}
