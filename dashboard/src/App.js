import React, { useState, useEffect, useCallback } from "react";
import { RecallMap } from "./components/RecallMap";
import { RecallFeed } from "./components/RecallFeed";
import { StatsPanel } from "./components/StatsPanel";
import { FilterBar } from "./components/FilterBar";
import "./App.css";

const API_BASE =
  process.env.REACT_APP_API_URL ||
  "/api";

function App() {
  const [recalls, setRecalls] = useState([]);
  const [stats, setStats] = useState(null);
  const [lastDataSyncAt, setLastDataSyncAt] = useState(null);
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
      const fetchedRecalls = data.recalls || [];
      setRecalls(fetchedRecalls);
      setLastDataSyncAt((current) => {
        const latestIngestedAt = getLatestIngestedAt(fetchedRecalls);
        return latestIngestedAt && (!current || latestIngestedAt > current)
          ? latestIngestedAt
          : current;
      });
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
      if (data.latest_ingested_at) {
        setLastDataSyncAt(data.latest_ingested_at);
      }
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

  const handleStateChange = (stateCode) => {
    setFilters((prev) => ({
      ...prev,
      state: stateCode,
    }));
  };

  return (
    <div className={`app ${darkMode ? "dark-mode" : ""}`}>
      <header className="app-header">
        <div className="header-content">
          <div className="hero-copy">
            <p className="eyebrow">Recall search dashboard</p>
            <h1>Find recalls and understand where risk is moving.</h1>
            <p className="subtitle">
              Search recent recalls by product, company, state, or recall reason,
              then filter the map and feed to focus on the risks that matter.
            </p>
          </div>
          <div className="site-actions">
            <button
              type="button"
              className="theme-toggle"
              onClick={() => setDarkMode((current) => !current)}
              aria-pressed={darkMode}
            >
              {darkMode ? "Light Mode" : "Dark Mode"}
            </button>
          </div>
        </div>
      </header>

      <FilterBar filters={filters} onChange={setFilters} />

      <main className="dashboard">
        <section className="main-column" aria-label="Recall search results">
          <section className="map-section" aria-label="Where recalls are happening">
            <div className="section-heading">
              <p className="eyebrow">By location</p>
              <h2>Where recalls are happening</h2>
              <p>
                Select a state to focus the recall list. Switch the map view to
                compare total volume, weighted risk, or Class I activity.
              </p>
            </div>
            <RecallMap
              stats={stats}
              selectedState={filters.state}
              onStateClick={handleStateClick}
            />
          </section>

          <RecallFeed
            recalls={recalls}
            loading={loading}
            lastUpdatedAt={lastDataSyncAt}
            selectedState={filters.state}
            onStateChange={handleStateChange}
          />
        </section>

        <aside className="sidebar">
          <StatsPanel stats={stats} recalls={recalls} loading={!stats} />
        </aside>
      </main>
    </div>
  );
}

function getLatestIngestedAt(recalls) {
  return recalls.reduce((latest, recall) => {
    const ingestedAt = recall.ingested_at;
    return ingestedAt && (!latest || ingestedAt > latest) ? ingestedAt : latest;
  }, null);
}

export default App;
