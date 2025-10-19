import React, { useState } from "react";

import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/Settings.css";
import { useTheme } from "./components/ThemeContext";

const settingsData = [
  {
    category: "Account",
    options: [
      { name: "Change Email", type: "button", variant: "danger" },
      { name: "Change Password", type: "button", variant: "danger" },
      { name: "Delete Account", type: "button", variant: "danger" },
    ],
  },
  {
    category: "Appearance",
    options: [
      { name: "Theme", type: "select", values: ["Light", "Silver"] },
      { name: "Font Size", type: "select", values: ["Small", "Medium", "Large"] },
    ],
  },
  {
    category: "Privacy",
    options: [
      { name: "Two-Factor Authentication", type: "toggle" },
      { name: "Activity Status", type: "toggle" },
    ],
  },
  {
    category: "Notifications",
    options: [
      { name: "Email Notifications", type: "toggle" },
      { name: "Push Notifications", type: "toggle" },
    ],
  },
];

export default function Settings() {
  const [activeCategory, setActiveCategory] = useState(settingsData[0].category);
  const [toggles, setToggles] = useState({});

  // 🔹 get theme and font settings from context
  const { theme, setTheme, fontSize, setFontSize } = useTheme();

  const handleToggle = (optionName) => {
    setToggles((prev) => ({ ...prev, [optionName]: !prev[optionName] }));
  };

  return (
    <div className="container-fluid vh-100 app-section">
      <div className="row h-100">
        {/* Sidebar */}
        <div className="col-12 col-md-3 col-lg-2 border-end p-0 settings-sidebar">
          <div className="list-group list-group-flush">
            <div className="list-group-item bg-primary text-white fw-bold">
              ⚙️ Settings
            </div>
            {settingsData.map((section) => (
              <button
                key={section.category}
                className={`list-group-item list-group-item-action ${
                  activeCategory === section.category ? "active" : ""
                }`}
                onClick={() => setActiveCategory(section.category)}
              >
                {section.category}
              </button>
            ))}
          </div>
        </div>

        {/* Main content */}
        <div className="col-12 col-md-9 col-lg-10 p-4">
          <div className="card shadow-sm settings-card">
            <div className="card-header fw-bold">
              {activeCategory}
            </div>
            <div className="card-body">
              {settingsData
                .find((section) => section.category === activeCategory)
                .options.map((option) => (
                  <div
                    key={option.name}
                    className="d-flex align-items-center justify-content-between py-2 border-bottom settings-option"
                  >
                    <span className="fw-medium">{option.name}</span>

                    {option.type === "button" && (
                      <button
                        className={`btn btn-sm ${
                          option.variant === "danger"
                            ? "btn-danger"
                            : "btn-outline-primary"
                        }`}
                      >
                        {option.name}
                      </button>
                    )}

                    {option.type === "select" && option.name === "Theme" && (
                      <select
                        className="form-select form-select-sm w-auto"
                        value={theme}
                        onChange={(e) => setTheme(e.target.value)}
                      >
                        {option.values.map((v) => (
                          <option key={v} value={v}>
                            {v}
                          </option>
                        ))}
                      </select>
                    )}

                    {option.type === "select" && option.name === "Font Size" && (
                      <select
                        className="form-select form-select-sm w-auto"
                        value={fontSize}
                        onChange={(e) => setFontSize(e.target.value)}
                      >
                        {option.values.map((v) => (
                          <option key={v} value={v}>
                            {v}
                          </option>
                        ))}
                      </select>
                    )}

                    {option.type === "toggle" && (
                      <div className="form-check form-switch">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          checked={toggles[option.name] || false}
                          onChange={() => handleToggle(option.name)}
                        />
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
