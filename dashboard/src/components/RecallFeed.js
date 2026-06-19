import React from "react";

const SEVERITY_COLORS = {
  "Class I": { bg: "#fef2f2", border: "#dc2626", text: "#991b1b", label: "CRITICAL" },
  "Class II": { bg: "#fff7ed", border: "#ea580c", text: "#9a3412", label: "MODERATE" },
  "Class III": { bg: "#fefce8", border: "#ca8a04", text: "#854d0e", label: "LOW" },
};

export function RecallFeed({ recalls, loading }) {
  if (loading) return <div className="feed-loading">Loading recalls...</div>;

  return (
    <div className="recall-feed">
      <h2>Recent Recalls</h2>
      {recalls.length === 0 && (
        <p className="no-results">No recalls match your filters.</p>
      )}
      {recalls.map((recall) => {
        const severity =
          SEVERITY_COLORS[recall.classification] || SEVERITY_COLORS["Class III"];
        return (
          <article
            key={recall.PK}
            className="recall-card"
            style={{ borderLeft: `4px solid ${severity.border}` }}
          >
            <div className="recall-header">
              <span
                className="severity-badge"
                style={{ background: severity.bg, color: severity.text }}
              >
                {severity.label}
              </span>
              <span className="recall-date">
                {formatDate(recall.report_date)}
              </span>
            </div>
            <h3 className="recall-firm">{recall.recalling_firm}</h3>
            <p className="recall-product">
              {truncate(recall.product_description, 120)}
            </p>
            <p className="recall-reason">
              {truncate(recall.reason_for_recall, 150)}
            </p>
            {recall.is_nationwide ? (
              <span className="distribution-tag nationwide">Nationwide</span>
            ) : (
              <span className="distribution-tag">
                {(recall.affected_states || []).join(", ")}
              </span>
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
