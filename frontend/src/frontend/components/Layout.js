import React from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout({ onContinueChat }) {
  return (
    <div className="d-flex app-container">
      <div style={{ width: "20%", minHeight: "100vh" }}>
        <Sidebar />
      </div>
      <div style={{ width: "80%", minHeight: "100vh" }}>
        <Outlet context={{ onContinueChat }} />
      </div>
    </div>
  );
}
