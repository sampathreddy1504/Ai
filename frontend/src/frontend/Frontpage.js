import React from 'react';
import '../styles/Homepage.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import { Link } from 'react-router-dom';

export default function Frontpage() {
  return (
    <div className="d-flex flex-column vh-100 overflow-hidden">
      {/* Navbar */}
      <nav className="navbar navbar-expand-lg navbar-dark bg-primary fixed-top m-0 p-0">
        <div className="container-fluid">
          <Link className="navbar-brand ms-3" to="/">MyAI Assistant</Link>
          <button
            className="navbar-toggler me-3"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#navbarNav"
          >
            <span className="navbar-toggler-icon"></span>
          </button>

          <div className="collapse navbar-collapse" id="navbarNav">
            <ul className="navbar-nav ms-auto me-3">
              <li className="nav-item">
                <Link className="nav-link active" to="/">Home</Link>
              </li>
              <li className="nav-item">
                <Link className="nav-link" to="/login">Login</Link>
              </li>
              <li className="nav-item">
                <Link className="nav-link" to="/signup">Signup</Link>
              </li>
            </ul>
          </div>
        </div>
      </nav>

      {/* Hero + Features Section */}
      <section className="flex-grow-1 hero-section d-flex flex-column justify-content-center align-items-center text-center">
        <div className="container">
          <h1 className="display-5 fw-bold">Welcome to Your Personal AI Assistant</h1>
          <p className="lead mt-3">
            Intelligent context-aware assistant that understands your queries and manages tasks effortlessly.
          </p>
          <Link to="/login" className="btn btn-primary btn-lg mt-3">Get Started</Link>

          {/* Features in the same viewport */}
          <div className="row mt-5 text-center">
            <div className="col-md-4 mb-3">
              <div className="card p-3 h-100">
                <div className="card-body">
                  <h5 className="card-title">Context Retention</h5>
                  <p className="card-text">Remembers past interactions to provide personalized responses.</p>
                </div>
              </div>
            </div>

            <div className="col-md-4 mb-3">
              <div className="card p-3 h-100">
                <div className="card-body">
                  <h5 className="card-title">Entity Extraction</h5>
                  <p className="card-text">Extracts all entities from any user query across multiple domains.</p>
                </div>
              </div>
            </div>

            <div className="col-md-4 mb-3">
              <div className="card p-3 h-100">
                <div className="card-body">
                  <h5 className="card-title">Intent Detection</h5>
                  <p className="card-text">Detects user intent to execute actions intelligently and efficiently.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-primary text-white text-center py-2 fixed-bottom">
        <p className="m-0">&copy; 2025 MyAI Assistant. All rights reserved.</p>
      </footer>
    </div>
  );
}
