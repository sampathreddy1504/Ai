import React from "react";
import { Link } from "react-router-dom";
import { FaUserCircle } from "react-icons/fa";
import "../styles/Profile.css";

export default function ProfileIcon({ name }) {
  return (
    <Link to="/profile" className="profile-icon-link d-flex align-items-center">
      <FaUserCircle size={26} className="me-2 profile-icon-img" />
      <span className="profile-icon-text">{name || "Profile"}</span>
    </Link>
  );
}
