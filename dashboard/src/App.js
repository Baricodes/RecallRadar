import React, { useState, useEffect, useCallback } from "react";
import { RecallMap } from "./components/RecallMap";
import { RecallFeed } from "./components/RecallFeed";
import { StatsPanel } from "./components/StatsPanel";
import { FilterBar } from "./components/FilterBar";
import "./App.css";

const API_BASE =
  process.env.REACT_APP_API_URL ||
  "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/v1";

function App() {
  const [recalls, setRecalls] = useState([]);
  const [stats, setStats] = useState(null);
  const [filters, setFilters] = useState({
    classification: null,
    state: null,
    status: "Ongoing",
  });
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem("recallradar-theme") === "dark";
  });
  const [loading, setLoading] = useState(true);

  const fetchRecalls = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    params.set("limit", "50");
    if (filters.classification) params.set("classification", filters.classification);
    if (filters.state) params.set("state", filters.state);
    if (filters.status) params.set("status", filters.status);

    try {
      const res = await fetch(`${API_BASE}/recalls?${params}`);
      const data = await res.json();
      setRecalls(data.recalls || []);
    } catch (err) {
      console.error("Failed to fetch recalls:", err);
    }
    setLoading(false);
  }, [filters]);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/recalls/stats`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    }
  }, []);

  useEffect(() => {
    fetchRecalls();
  }, [fetchRecalls]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    localStorage.setItem("recallradar-theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  const handleStateClick = (stateCode) => {
    setFilters((prev) => ({
      ...prev,
      state: prev.state === stateCode ? null : stateCode,
    }));
  };

  return (
    <div className={`app ${darkMode ? "dark-mode" : ""}`}>
      <header className="app-header">
        <div className="header-content">
          <div>
            <h1>RecallRadar</h1>
            <p className="subtitle">
              Real-time FDA food recall intelligence across the United States
            </p>
          </div>
          <button
            type="button"
            className="theme-toggle"
            onClick={() => setDarkMode((current) => !current)}
            aria-pressed={darkMode}
          >
            {darkMode ? "Light Mode" : "Dark Mode"}
          </button>
        </div>
      </header>

      <FilterBar filters={filters} onChange={setFilters} />

      <main className="dashboard">
        <section className="map-section">
          <RecallMap
            stats={stats}
            recalls={recalls}
            selectedState={filters.state}
            onStateClick={handleStateClick}
          />
        </section>

        <aside className="sidebar">
          <StatsPanel stats={stats} recalls={recalls} loading={!stats} />
          <RecallFeed recalls={recalls} loading={loading} />
        </aside>
      </main>
    </div>
  );
}

export default App;
