import React, { useState, useEffect, useCallback } from "react";
import { Calendar, dateFnsLocalizer, Views } from "react-big-calendar";
import {
  format,
  parse,
  startOfWeek,
  getDay,
  isSameDay,
  addDays,
  subDays,
} from "date-fns";
import { enUS } from "date-fns/locale";
import "react-big-calendar/lib/css/react-big-calendar.css";
import "bootstrap/dist/css/bootstrap.min.css";
import { Modal, Button, Form, ListGroup, Badge, Spinner } from "react-bootstrap";
import axios from "axios";
import "../styles/Calendar.css";

const locales = { "en-US": enUS };
const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
});

export default function MyCalendar() {
  const [events, setEvents] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [currentView, setCurrentView] = useState(Views.MONTH);
  const [showModal, setShowModal] = useState(false);
  const [newEventTitle, setNewEventTitle] = useState("");
  const [newEventSlot, setNewEventSlot] = useState({ start: null, end: null });
  const [showDayModal, setShowDayModal] = useState(false);
  const [selectedDayEvents, setSelectedDayEvents] = useState([]);
  const [selectedDay, setSelectedDay] = useState(null);

  // Load tasks from backend
  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      const token = localStorage.getItem("authToken");
      if (!token) return;

      const response = await axios.get("/api/tasks", { params: { token } });
      if (response.data.success) {
        const taskEvents = response.data.tasks.map((task) => ({
          id: task.id,
          title: task.title,
          start: new Date(task.datetime),
          end: new Date(new Date(task.datetime).getTime() + 60 * 60 * 1000),
          type: "task",
          priority: task.priority,
          category: task.category,
          notes: task.notes,
        }));
        setTasks(taskEvents);
        setEvents(taskEvents);
      }
    } catch (error) {
      console.error("Failed to load tasks:", error);
    } finally {
      setLoading(false);
    }
  };

  // Open modal to add event
  const handleSelectSlot = ({ start, end }) => {
    setNewEventSlot({ start, end });
    setShowModal(true);
  };

  const handleSaveEvent = () => {
    if (newEventTitle.trim() === "") return;
    const newEvent = {
      id: Date.now(),
      title: newEventTitle,
      start: newEventSlot.start,
      end: newEventSlot.end,
      type: "custom",
    };
    setEvents([...events, newEvent]);
    setNewEventTitle("");
    setShowModal(false);
  };

  const handleDeleteEvent = async (id) => {
    try {
      const token = localStorage.getItem("authToken");
      const eventToDelete = events.find((e) => e.id === id);

      if (eventToDelete?.type === "task" && token) {
        await axios.delete(`/api/tasks/${id}`, { params: { token } });
      }

      setEvents(events.filter((e) => e.id !== id));
      setTasks(tasks.filter((t) => t.id !== id));
    } catch (error) {
      console.error("Failed to delete task:", error);
    }
  };

  // Handle click on a day
  const handleDayClick = (slotInfo) => {
    const clickedDate = slotInfo.start;
    const dayEvents = events.filter((e) => isSameDay(e.start, clickedDate));
    if (dayEvents.length > 0) {
      setSelectedDay(clickedDate);
      setSelectedDayEvents(dayEvents);
      setShowDayModal(true);
    }
  };

  // Custom event colors
  const eventPropGetter = (event) => {
    const isTask = event.type === "task";
    let priorityColor = "#007bff";
    if (isTask) {
      const colorMap = {
        high: "#dc3545",
        medium: "#ffc107",
        low: "#28a745",
      };
      priorityColor = colorMap[event.priority] || "#007bff";
    }
    return {
      style: {
        backgroundColor: isTask ? priorityColor : "#6366f1",
        color: "white",
        borderRadius: "6px",
        border: "none",
        padding: "3px 6px",
        fontSize: "13px",
        boxShadow: "0 1px 4px rgba(0,0,0,0.1)",
        transition: "transform 0.2s ease",
      },
    };
  };

  // ✅ Custom Toolbar for navigation & view control
  const CustomToolbar = useCallback(
    ({ label, onNavigate, onView }) => (
      <div className="calendar-toolbar d-flex justify-content-between align-items-center mb-3">
        <div className="d-flex align-items-center gap-2">
          <Button
            variant="outline-primary"
            size="sm"
            onClick={() => onNavigate("TODAY")}
          >
            Today
          </Button>
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={() => onNavigate("PREV")}
          >
            ← Back
          </Button>
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={() => onNavigate("NEXT")}
          >
            Next →
          </Button>
        </div>

        <h5 className="calendar-header mb-0">{label}</h5>

        <div className="d-flex align-items-center gap-2">
          <Button
            variant={currentView === Views.MONTH ? "primary" : "outline-primary"}
            size="sm"
            onClick={() => {
              setCurrentView(Views.MONTH);
              onView(Views.MONTH);
            }}
          >
            Month
          </Button>
          <Button
            variant={currentView === Views.WEEK ? "primary" : "outline-primary"}
            size="sm"
            onClick={() => {
              setCurrentView(Views.WEEK);
              onView(Views.WEEK);
            }}
          >
            Week
          </Button>
          <Button
            variant={currentView === Views.DAY ? "primary" : "outline-primary"}
            size="sm"
            onClick={() => {
              setCurrentView(Views.DAY);
              onView(Views.DAY);
            }}
          >
            Day
          </Button>
          <Button variant="success" size="sm" onClick={() => setShowModal(true)}>
            + Add
          </Button>
        </div>
      </div>
    ),
    [currentView]
  );

  return (
    <div className="calendar-container fade-in">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h3 className="calendar-title mb-1">📅 My Professional Calendar</h3>
          <p className="calendar-subtext">Manage tasks, events, and reminders visually</p>
        </div>
        <Button
          variant="outline-primary"
          size="sm"
          onClick={loadTasks}
          disabled={loading}
        >
          {loading ? (
            <>
              <Spinner size="sm" animation="border" className="me-2" /> Loading
            </>
          ) : (
            "🔄 Refresh"
          )}
        </Button>
      </div>

      <div className="calendar-wrapper shadow-sm">
        <Calendar
          localizer={localizer}
          culture="en-US"
          events={events}
          startAccessor="start"
          endAccessor="end"
          style={{ height: "75vh" }}
          selectable
          components={{ toolbar: CustomToolbar }}
          onSelectSlot={handleDayClick}
          onNavigate={(date) => setCurrentDate(date)}
          eventPropGetter={eventPropGetter}
          view={currentView}
          onView={setCurrentView}
          date={currentDate}
        />
      </div>

      {/* Add Event Modal */}
      <Modal show={showModal} onHide={() => setShowModal(false)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Add Event</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group controlId="eventTitle">
              <Form.Label>Event Title</Form.Label>
              <Form.Control
                type="text"
                placeholder="Enter event title"
                value={newEventTitle}
                onChange={(e) => setNewEventTitle(e.target.value)}
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSaveEvent}>
            Save
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Day Details Modal */}
      <Modal show={showDayModal} onHide={() => setShowDayModal(false)} centered size="lg">
        <Modal.Header closeButton>
          <Modal.Title>
            📆 Tasks on {selectedDay ? format(selectedDay, "EEEE, MMMM d yyyy") : ""}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedDayEvents.length > 0 ? (
            <ListGroup variant="flush">
              {selectedDayEvents.map((e) => (
                <ListGroup.Item
                  key={e.id}
                  className="d-flex justify-content-between align-items-center flex-column flex-md-row"
                >
                  <div className="task-info">
                    <h6 className="mb-1">
                      {e.title}{" "}
                      {e.type === "task" && e.priority && (
                        <Badge
                          bg={
                            e.priority === "high"
                              ? "danger"
                              : e.priority === "medium"
                              ? "warning"
                              : "success"
                          }
                          className="ms-2"
                        >
                          {e.priority}
                        </Badge>
                      )}
                    </h6>
                    <small className="text-muted">
                      {format(e.start, "hh:mm a")} - {format(e.end, "hh:mm a")}{" "}
                      {e.type === "task" && e.category && (
                        <span className="ms-2">📂 {e.category}</span>
                      )}
                    </small>
                    {e.type === "task" && e.notes && (
                      <div className="mt-1">
                        <small className="text-muted">{e.notes}</small>
                      </div>
                    )}
                  </div>
                  <Button
                    variant="outline-danger"
                    size="sm"
                    onClick={() => handleDeleteEvent(e.id)}
                  >
                    Delete
                  </Button>
                </ListGroup.Item>
              ))}
            </ListGroup>
          ) : (
            <p className="text-muted text-center my-3">No tasks for this day.</p>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowDayModal(false)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}
