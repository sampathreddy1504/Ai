import React, { useState, useEffect } from "react";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/Tasks.css";

export default function Tasks() {
  const [activeTab, setActiveTab] = useState("all");
  const [tasks, setTasks] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");

  // Fetch tasks from backend or local storage
  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const token = localStorage.getItem("authToken");
        const response = await fetch(
          `/api/tasks?token=${encodeURIComponent(token || "")}`
        );
        const data = await response.json();

        if (data.success && Array.isArray(data.tasks)) {
          const formattedTasks = data.tasks.map((task) => ({
            id: task.id,
            title: task.title,
            status: task.notified ? "completed" : "pending",
            datetime: task.datetime,
          }));

          const sorted = formattedTasks.sort(
            (a, b) => new Date(a.datetime) - new Date(b.datetime)
          );

          setTasks(sorted);
          localStorage.setItem("tasks", JSON.stringify(sorted));
        } else {
          // Fallback: Load from localStorage if API fails
          const local = JSON.parse(localStorage.getItem("tasks") || "[]");
          setTasks(local);
          console.warn("Loaded tasks from local storage.");
        }
      } catch (err) {
        console.error("Error fetching tasks:", err);
        const local = JSON.parse(localStorage.getItem("tasks") || "[]");
        setTasks(local);
      }
    };

    fetchTasks();
  }, []);

  // Filter & Search
  const filteredTasks = tasks
    .filter((t) => (activeTab === "all" ? true : t.status === activeTab))
    .filter((t) => t.title.toLowerCase().includes(searchTerm.toLowerCase()));

  // Add Task
  const handleAddTask = () => {
    const title = prompt("Enter task title:");
    if (!title) return;

    const datetime = prompt(
      "Enter date and time (YYYY-MM-DD HH:MM):",
      new Date().toISOString().slice(0, 16).replace("T", " ")
    );
    if (!datetime) return;

    const newTask = {
      id: Date.now(),
      title,
      status: "pending",
      datetime: new Date(datetime).toISOString(),
    };

    const updated = [...tasks, newTask].sort(
      (a, b) => new Date(a.datetime) - new Date(b.datetime)
    );

    setTasks(updated);
    localStorage.setItem("tasks", JSON.stringify(updated));

    alert("✅ Task added successfully!");
  };

  // Delete Task
  const handleRemoveTask = async (id) => {
    try {
      const token = localStorage.getItem("authToken");
      if (token) {
        await fetch(`/api/tasks/${id}?token=${encodeURIComponent(token)}`, {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
        });
      }

      const updated = tasks.filter((task) => task.id !== id);
      setTasks(updated);
      localStorage.setItem("tasks", JSON.stringify(updated));

      alert("🗑️ Task removed successfully!");
    } catch (error) {
      console.error("Failed to delete task:", error);
    }
  };

  // Toggle Status
  const handleToggleStatus = (id) => {
    const updated = tasks.map((task) => {
      if (task.id !== id) return task;
      const newStatus = task.status === "completed" ? "pending" : "completed";
      // Optimistic UI update
      const updatedTask = { ...task, status: newStatus };
      // Persist change to backend if authenticated
      const token = localStorage.getItem("authToken");
      if (token) {
        fetch(`/api/tasks/${id}/status?token=${encodeURIComponent(token)}&status=${encodeURIComponent(newStatus)}`, {
          method: "PATCH",
        }).catch((err) => console.error("Failed to update task status:", err));
      }
      return updatedTask;
    });

    setTasks(updated);
    localStorage.setItem("tasks", JSON.stringify(updated));
  };

  // Clear all completed
  const handleClearCompleted = async () => {
    if (!window.confirm("Are you sure you want to clear all completed tasks?")) return;

    try {
      const token = localStorage.getItem("authToken");
      // If a token exists, call backend to remove completed tasks server-side
      if (token) {
        await fetch(`/api/tasks/clear_completed?token=${encodeURIComponent(token)}`, {
          method: "DELETE",
        });
        // refetch tasks from server to get authoritative list
        const response = await fetch(`/api/tasks?token=${encodeURIComponent(token || "")}`);
        const data = await response.json();
        if (data.success && Array.isArray(data.tasks)) {
          const formattedTasks = data.tasks.map((task) => ({
            id: task.id,
            title: task.title,
            status: task.notified ? "completed" : "pending",
            datetime: task.datetime,
          }));
          const sorted = formattedTasks.sort((a, b) => new Date(a.datetime) - new Date(b.datetime));
          setTasks(sorted);
          localStorage.setItem("tasks", JSON.stringify(sorted));
          return;
        }
      }

      // Fallback: client-side only
      const pending = tasks.filter((t) => t.status !== "completed");
      setTasks(pending);
      localStorage.setItem("tasks", JSON.stringify(pending));
    } catch (err) {
      console.error("Failed to clear completed tasks:", err);
    }
  };

  return (
    <div className="tasks-page container mt-4 fade-in">
      {/* Header */}
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h4>Tasks & Reminders</h4>
          <small>
            {tasks.filter((t) => t.status === "pending").length} pending,{" "}
            {tasks.filter((t) => t.status === "completed").length} completed
          </small>
        </div>

        <div className="d-flex gap-2">
          <button className="btn btn-primary" onClick={handleAddTask}>
            + Add Task
          </button>
          <button
            className="btn btn-clear-completed"
            onClick={handleClearCompleted}
          >
            Clear Completed
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="mb-3">
        <input
          type="text"
          className="form-control"
          placeholder="🔍 Search tasks..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {/* Tabs */}
      <ul className="nav nav-tabs">
        {["all", "pending", "completed"].map((tab) => (
          <li key={tab} className="nav-item">
            <button
              className={`nav-link ${activeTab === tab ? "active" : ""}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          </li>
        ))}
      </ul>

      {/* Task List */}
      <div className="p-4">
        {filteredTasks.length > 0 ? (
          <div className="tasks-scroll-container" data-testid="tasks-scroll">
            <ul className="list-group">
              {filteredTasks.map((task) => {
              const isOverdue =
                new Date(task.datetime) < new Date() &&
                task.status !== "completed";
              return (
                <li
                  key={task.id}
                  className={`list-group-item d-flex justify-content-between align-items-center flex-column flex-md-row ${
                    isOverdue ? "overdue" : ""
                  }`}
                >
                  <div style={{ flex: 1 }}>
                    <strong>{task.title}</strong>
                    <br />
                    <small>
                      {new Date(task.datetime).toLocaleString(undefined, {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </small>
                  </div>

                  <div className="d-flex gap-2 align-items-center">
                    <span
                      className={`badge ${
                        task.status === "completed"
                          ? "bg-success"
                          : "bg-warning text-dark"
                      } clickable`}
                      onClick={() => handleToggleStatus(task.id)}
                      title="Click to toggle status"
                    >
                      {task.status}
                    </span>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleRemoveTask(task.id)}
                    >
                      Remove
                    </button>
                  </div>
                </li>
              );
              })}
            </ul>
          </div>
        ) : (
          <div className="text-center mt-4">
            <p>
              <strong>No tasks found</strong>
            </p>
            <p>Create your first task to get started!</p>
          </div>
        )}
      </div>
    </div>
  );
}
