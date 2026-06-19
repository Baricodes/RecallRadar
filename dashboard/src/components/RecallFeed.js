import React, { useMemo, useState } from "react";

const SEVERITY_COLORS = {
  "Class I": { bg: "#fef2f2", border: "#dc2626", text: "#991b1b", label: "CRITICAL" },
  "Class II": { bg: "#fff7ed", border: "#ea580c", text: "#9a3412", label: "MODERATE" },
  "Class III": { bg: "#fefce8", border: "#ca8a04", text: "#854d0e", label: "LOW" },
};

export function RecallFeed({ recalls, loading }) {
  const [firmQuery, setFirmQuery] = useState("");
  const [productQuery, setProductQuery] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [severityFilters, setSeverityFilters] = useState([]);
  const [expandedView, setExpandedView] = useState(false);
  const [expandedRows, setExpandedRows] = useState({});

  const stateOptions = useMemo(() => {
    const states = new Set();
    recalls.forEach((recall) => {
      (recall.affected_states || []).forEach((state) => states.add(state));
    });
    return Array.from(states).sort();
  }, [recalls]);

  const filteredRecalls = useMemo(() => {
    const firmTerm = firmQuery.trim().toLowerCase();
    const productTerm = productQuery.trim().toLowerCase();

    return recalls.filter((recall) => {
      const firmMatches =
        !firmTerm ||
        (recall.recalling_firm || "").toLowerCase().includes(firmTerm);
      const productMatches =
        !productTerm ||
        (recall.product_description || "").toLowerCase().includes(productTerm);
      const stateMatches =
        !stateFilter || (recall.affected_states || []).includes(stateFilter);
      const severityMatches =
        severityFilters.length === 0 ||
        severityFilters.includes(recall.classification);

      return firmMatches && productMatches && stateMatches && severityMatches;
    });
  }, [firmQuery, productQuery, recalls, severityFilters, stateFilter]);

  if (loading) return <div className="feed-loading">Loading recalls...</div>;

  const toggleSeverity = (classification) => {
    setSeverityFilters((current) =>
      current.includes(classification)
        ? current.filter((item) => item !== classification)
        : [...current, classification]
    );
  };

  const toggleRow = (recallId) => {
    setExpandedRows((current) => ({
      ...current,
      [recallId]: !current[recallId],
    }));
  };

  return (
    <div className="recall-feed">
      <div className="feed-header">
        <h2>Recent Recalls</h2>
        <button
          type="button"
          className="view-toggle"
          onClick={() => setExpandedView((current) => !current)}
        >
          {expandedView ? "Compact View" : "Expanded View"}
        </button>
      </div>

      <div className="feed-filter-panel">
        <input
          type="search"
          value={firmQuery}
          onChange={(event) => setFirmQuery(event.target.value)}
          placeholder="Search firm"
          aria-label="Search by firm name"
        />
        <input
          type="search"
          value={productQuery}
          onChange={(event) => setProductQuery(event.target.value)}
          placeholder="Product keyword"
          aria-label="Search by product keyword"
        />
        <select
          value={stateFilter}
          onChange={(event) => setStateFilter(event.target.value)}
          aria-label="Filter by affected state"
        >
          <option value="">All states</option>
          {stateOptions.map((state) => (
            <option key={state} value={state}>
              {state}
            </option>
          ))}
        </select>
        <div className="feed-severity-filters" aria-label="Filter by severity">
          {Object.keys(SEVERITY_COLORS).map((classification) => (
            <button
              key={classification}
              type="button"
              className={`severity-filter ${
                severityFilters.includes(classification) ? "active" : ""
              }`}
              style={{
                "--severity-color": SEVERITY_COLORS[classification].border,
                "--severity-bg": SEVERITY_COLORS[classification].bg,
                "--severity-text": SEVERITY_COLORS[classification].text,
              }}
              onClick={() => toggleSeverity(classification)}
            >
              {classification}
            </button>
          ))}
        </div>
      </div>

      {filteredRecalls.length === 0 && (
        <p className="no-results">No recalls match your filters.</p>
      )}
      {filteredRecalls.map((recall) => {
        const severity =
          SEVERITY_COLORS[recall.classification] || SEVERITY_COLORS["Class III"];
        const recallId = recall.PK || `${recall.recalling_firm}-${recall.report_date}`;
        const showDetails = expandedView || expandedRows[recallId];
        const stateCount = recall.is_nationwide
          ? "Nationwide"
          : `${(recall.affected_states || []).length} states`;

        return (
          <article
            key={recallId}
            className={`recall-card ${showDetails ? "expanded" : "compact"}`}
            style={{ borderLeft: `4px solid ${severity.border}` }}
          >
            <button
              type="button"
              className="recall-row"
              onClick={() => toggleRow(recallId)}
              aria-expanded={showDetails}
            >
              <span className="recall-row-main">
                <span
                  className="severity-badge"
                  style={{ background: severity.bg, color: severity.text }}
                >
                  {severity.label}
                </span>
                <span className="recall-firm">{recall.recalling_firm}</span>
              </span>
              <span className="recall-row-meta">
                <span className="recall-date">
                  {formatDate(recall.report_date)}
                </span>
                <span className="state-count">{stateCount}</span>
              </span>
            </button>

            {showDetails && (
              <div className="recall-details">
                <p className="recall-product">
                  {truncate(recall.product_description, 160)}
                </p>
                <p className="recall-reason">
                  {truncate(recall.reason_for_recall, 180)}
                </p>
                {recall.is_nationwide ? (
                  <span className="distribution-tag nationwide">Nationwide</span>
                ) : (
                  <span
                    className="distribution-tag"
                    title={(recall.affected_states || []).join(", ")}
                  >
                    {(recall.affected_states || []).join(", ")}
                  </span>
                )}
              </div>
            )}
          </article>
        );
      })}
    </div>
  );
}

function formatDate(dateStr) {
  if (!dateStr || dateStr.length !== 8) return dateStr;
  return `${dateStr.slice(4, 6)}/${dateStr.slice(6, 8)}/${dateStr.slice(0, 4)}`;
}

function truncate(str, max) {
  if (!str) return "";
  return str.length > max ? str.slice(0, max) + "..." : str;
}
