import React from "react";

const SEVERITY_COLORS = {
  "Class I": "#dc2626",
  "Class II": "#ea580c",
  "Class III": "#ca8a04",
};

const SEVERITY_LABELS = {
  "Class I": "High Risk",
  "Class II": "Medium Risk",
  "Class III": "Low Risk",
};

export function FilterBar({ filters, onChange }) {
  const update = (key, value) => {
    onChange((prev) => ({
      ...prev,
      [key]: prev[key] === value ? null : value,
    }));
  };

  return (
    <div className="filter-bar">
      <div className="filter-group">
        <label>Risk level</label>
        <div className="filter-buttons">
          {["Class I", "Class II", "Class III"].map((cls) => (
            <button
              key={cls}
              type="button"
              className={`filter-btn ${filters.classification === cls ? "active" : ""}`}
              style={{ "--severity-color": SEVERITY_COLORS[cls] }}
              onClick={() => update("classification", cls)}
            >
              {SEVERITY_LABELS[cls]}
            </button>
          ))}
        </div>
        <details className="risk-help">
          <summary>What do these mean?</summary>
          <p>
            FDA recall classes describe how likely a recalled product is to cause
            harm. RecallRadar translates them into plain risk levels.
          </p>
          <ul>
            <li>
              <strong>High Risk:</strong> serious health consequences are possible.
            </li>
            <li>
              <strong>Medium Risk:</strong> temporary or reversible health effects are possible.
            </li>
            <li>
              <strong>Low Risk:</strong> adverse health effects are unlikely.
            </li>
          </ul>
        </details>
      </div>

      <div className="filter-group">
        <label>Status</label>
        <div className="filter-buttons">
          {["Ongoing", "Completed", "Terminated"].map((status) => (
            <button
              key={status}
              type="button"
              className={`filter-btn ${filters.status === status ? "active" : ""}`}
              onClick={() => update("status", status)}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {filters.state && (
        <div className="active-filter">
          Showing: {filters.state}
          <button
            type="button"
            onClick={() => update("state", null)}
            className="clear-btn"
            aria-label={`Clear ${filters.state} state filter`}
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}
