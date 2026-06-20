import React, { useEffect, useMemo, useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { List } from "react-window";

const SEVERITY_COLORS = {
  "Class I": { bg: "#fef2f2", border: "#dc2626", text: "#991b1b", label: "High Risk" },
  "Class II": { bg: "#fff7ed", border: "#ea580c", text: "#9a3412", label: "Medium Risk" },
  "Class III": { bg: "#fefce8", border: "#ca8a04", text: "#854d0e", label: "Low Risk" },
};

const COMPACT_ROW_HEIGHT = 110;
const EXPANDED_ROW_HEIGHT = 250;
const MAX_LIST_HEIGHT = 520;

export function RecallFeed({ recalls, loading, lastUpdatedAt }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [expandedView, setExpandedView] = useState(false);
  const [expandedRows, setExpandedRows] = useState({});
  const [relativeUpdatedAt, setRelativeUpdatedAt] = useState(() =>
    formatRelativeTime(lastUpdatedAt)
  );

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 250);

    return () => window.clearTimeout(timeoutId);
  }, [searchQuery]);

  useEffect(() => {
    const updateRelativeTime = () => {
      setRelativeUpdatedAt(formatRelativeTime(lastUpdatedAt));
    };

    updateRelativeTime();
    const intervalId = window.setInterval(updateRelativeTime, 60000);
    return () => window.clearInterval(intervalId);
  }, [lastUpdatedAt]);

  const stateOptions = useMemo(() => {
    const states = new Set();
    recalls.forEach((recall) => {
      (recall.affected_states || []).forEach((state) => states.add(state));
    });
    return Array.from(states).sort();
  }, [recalls]);

  const filteredRecalls = useMemo(() => {
    const searchTerm = debouncedSearchQuery.trim().toLowerCase();

    return recalls.filter((recall) => {
      const searchMatches =
        !searchTerm ||
        [
          recall.recalling_firm,
          recall.product_description,
          recall.reason_for_recall,
        ]
          .filter(Boolean)
          .some((value) => value.toLowerCase().includes(searchTerm));
      const stateMatches =
        !stateFilter || (recall.affected_states || []).includes(stateFilter);

      return searchMatches && stateMatches;
    });
  }, [debouncedSearchQuery, recalls, stateFilter]);

  const rowHeight = useMemo(
    () => (index) => {
      const recall = filteredRecalls[index];
      const recallId = getRecallId(recall);
      return expandedView || expandedRows[recallId]
        ? EXPANDED_ROW_HEIGHT
        : COMPACT_ROW_HEIGHT;
    },
    [expandedRows, expandedView, filteredRecalls]
  );

  let totalListHeight = 0;
  for (let index = 0; index < filteredRecalls.length; index += 1) {
    totalListHeight += rowHeight(index);
  }
  const listHeight = Math.min(MAX_LIST_HEIGHT, totalListHeight);
  const listKey = [
    debouncedSearchQuery,
    stateFilter,
    expandedView ? "expanded" : "compact",
  ].join("::");

  if (loading) {
    return (
      <div className="feed-loading" role="status">
        <span className="loading-spinner" aria-hidden="true" />
        Loading recalls...
      </div>
    );
  }

  const toggleRow = (recallId) => {
    setExpandedRows((current) => ({
      ...current,
      [recallId]: !current[recallId],
    }));
  };

  return (
    <div className="recall-feed">
      <div className="feed-header">
        <div>
          <p className="eyebrow">Search recalls</p>
          <h2>Recent Food Recalls</h2>
          <p className="feed-updated">
            {relativeUpdatedAt
              ? `Latest FDA sync: ${relativeUpdatedAt}`
              : "Latest FDA sync unavailable"}
          </p>
        </div>
        <button
          type="button"
          className="view-toggle"
          onClick={() => setExpandedView((current) => !current)}
        >
          {expandedView ? "Show Less" : "Show Details"}
        </button>
      </div>

      <div className="feed-filter-panel">
        <input
          type="search"
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Search product, company, or recall reason"
          aria-label="Search recalls by firm, product, or reason"
          className="feed-search"
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
      </div>

      {filteredRecalls.length === 0 && (
        <p className="no-results">No recalls match your search and filters.</p>
      )}
      {filteredRecalls.length > 0 && (
        <List
          key={listKey}
          className="recall-list"
          rowComponent={RecallRow}
          rowCount={filteredRecalls.length}
          rowHeight={rowHeight}
          rowProps={{
            expandedRows,
            expandedView,
            recalls: filteredRecalls,
            toggleRow,
          }}
          overscanCount={3}
          style={{ height: listHeight, width: "100%" }}
        />
      )}
    </div>
  );
}

function RecallRow({ index, style, recalls, expandedRows, expandedView, toggleRow }) {
  const recall = recalls[index];
  const severity =
    SEVERITY_COLORS[recall.classification] || SEVERITY_COLORS["Class III"];
  const recallId = getRecallId(recall);
  const showDetails = expandedView || expandedRows[recallId];
  const stateCount = recall.is_nationwide
    ? "Nationwide"
    : `${(recall.affected_states || []).length} states`;

  return (
    <div style={style}>
      <article
        className={`recall-card ${showDetails ? "expanded" : "compact"}`}
        style={{ borderLeft: `4px solid ${severity.border}` }}
      >
        <div className="recall-row">
          <span className="recall-row-main">
            <span
              className="severity-badge"
              style={{ background: severity.bg, color: severity.text }}
            >
              {severity.label}
            </span>
            <span className="recall-title-group">
              <span className="recall-product-title">
                {recall.product_description || "Product not listed"}
              </span>
              <span className="recall-firm">{recall.recalling_firm}</span>
            </span>
          </span>
          <span className="recall-row-meta">
            <span className="recall-date">{formatDate(recall.report_date)}</span>
            <span className="state-count">{stateCount}</span>
            <button
              type="button"
              className="recall-details-toggle"
              onClick={() => toggleRow(recallId)}
              aria-expanded={showDetails}
            >
              {showDetails ? "Hide" : "Details"}
            </button>
          </span>
        </div>

        {showDetails && (
          <div className="recall-details">
            <p className="recall-reason">
              <strong>Reason:</strong> {truncate(recall.reason_for_recall, 180)}
            </p>
            <p className="recall-action">
              <strong>What should I do?</strong> {getActionGuidance(recall)}
            </p>
            <p className="recall-product">
              <strong>FDA class:</strong> {recall.classification}
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
    </div>
  );
}

function formatDate(dateStr) {
  if (!dateStr || dateStr.length !== 8) return dateStr;
  return `${dateStr.slice(4, 6)}/${dateStr.slice(6, 8)}/${dateStr.slice(0, 4)}`;
}

function formatRelativeTime(dateStr) {
  if (!dateStr) return "";

  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return "";

  return `${formatDistanceToNow(date)} ago`;
}

function getRecallId(recall) {
  return recall.PK || `${recall.recalling_firm}-${recall.report_date}`;
}

function getActionGuidance(recall) {
  const scope = recall.is_nationwide
    ? "This recall was distributed nationwide."
    : "Check whether the product was distributed in your state.";

  if (recall.classification === "Class I") {
    return `${scope} If you may have this product, do not consume it and follow FDA or company instructions.`;
  }

  return `${scope} Compare the product details with items you have at home and follow FDA or company instructions.`;
}

function truncate(str, max) {
  if (!str) return "";
  return str.length > max ? str.slice(0, max) + "..." : str;
}
