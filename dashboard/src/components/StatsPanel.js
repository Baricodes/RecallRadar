import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const CLASS_COLORS = {
  "Class I": "#dc2626",
  "Class II": "#ea580c",
  "Class III": "#ca8a04",
};

export function StatsPanel({ stats, recalls = [], loading }) {
  if (loading || !stats) {
    return <div className="stats-loading">Loading stats...</div>;
  }

  const classData = Object.entries(stats.by_classification || {}).map(
    ([name, value]) => ({ name, value })
  );
  const classTotal = classData.reduce((sum, item) => sum + item.value, 0);
  const firmDetails = buildFirmDetails(recalls);

  const firmData = Object.entries(stats.top_firms || {})
    .slice(0, 5)
    .map(([name, value]) => ({
      name: name.length > 20 ? name.slice(0, 18) + "..." : name,
      fullName: name,
      value,
      details: firmDetails[name],
    }));

  return (
    <div className="stats-panel">
      <h2>Overview</h2>

      <div className="stat-cards">
        <div className="stat-card">
          <span className="stat-number">
            {stats.total_recalls?.toLocaleString()}
          </span>
          <span className="stat-label">Total Recalls</span>
        </div>
        <div className="stat-card">
          <span className="stat-number">
            {stats.by_classification?.["Class I"] || 0}
          </span>
          <span className="stat-label critical">Class I (Critical)</span>
        </div>
        <div className="stat-card">
          <span className="stat-number">{stats.nationwide_percentage}%</span>
          <span
            className="stat-label"
            title="Percentage of recalls distributed across all 50 states."
          >
            Nationwide Scope
          </span>
        </div>
      </div>

      <div className="classification-summary">
        <div className="classification-summary-header">
          <h3>By Classification</h3>
          <span>{classTotal.toLocaleString()} recalls</span>
        </div>
        <div className="classification-stack" aria-label="Recall classification breakdown">
          {classData.map((entry) => {
            const width = classTotal ? (entry.value / classTotal) * 100 : 0;
            return (
              <div
                key={entry.name}
                className="classification-segment"
                style={{
                  width: `${width}%`,
                  background: CLASS_COLORS[entry.name] || "#888",
                }}
                title={`${entry.name}: ${entry.value.toLocaleString()}`}
              >
                {width >= 16 ? entry.value.toLocaleString() : ""}
              </div>
            );
          })}
        </div>
        <div className="classification-legend">
          {classData.map((entry) => (
            <span key={entry.name}>
              <span
                className="legend-dot"
                style={{ background: CLASS_COLORS[entry.name] || "#888" }}
              />
              {entry.name}: {entry.value.toLocaleString()}
            </span>
          ))}
        </div>
      </div>

      <h3>Top Firms</h3>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={firmData} layout="vertical">
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="name"
            width={100}
            tick={{ fontSize: 11 }}
          />
          <Tooltip content={<FirmTooltip />} />
          <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function FirmTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;

  const firm = payload[0].payload;
  const details = firm.details;

  return (
    <div className="chart-tooltip">
      <strong>{firm.fullName}</strong>
      <span>{firm.value.toLocaleString()} total recalls</span>
      {details ? (
        <>
          <span>
            {Object.entries(details.classifications)
              .filter(([, count]) => count > 0)
              .map(([name, count]) => `${name}: ${count}`)
              .join(", ")}
          </span>
          <span>
            States: {details.states.length ? details.states.join(", ") : "Not listed"}
          </span>
          <span>
            Top products:{" "}
            {details.products.length ? details.products.join("; ") : "Not listed"}
          </span>
        </>
      ) : (
        <span>Detailed breakdown appears when this firm is in recent recalls.</span>
      )}
    </div>
  );
}

function buildFirmDetails(recalls) {
  const details = recalls.reduce((acc, recall) => {
    const firmName = recall.recalling_firm || "Unknown";
    if (!acc[firmName]) {
      acc[firmName] = {
        classifications: { "Class I": 0, "Class II": 0, "Class III": 0 },
        states: new Set(),
        products: new Set(),
      };
    }

    const firm = acc[firmName];
    firm.classifications[recall.classification] =
      (firm.classifications[recall.classification] || 0) + 1;
    (recall.affected_states || []).forEach((state) => firm.states.add(state));
    if (recall.product_description) {
      firm.products.add(truncate(recall.product_description, 48));
    }

    return acc;
  }, {});

  Object.values(details).forEach((firm) => {
    firm.states = Array.from(firm.states).sort();
    firm.products = Array.from(firm.products).slice(0, 3);
  });

  return details;
}

function truncate(str, max) {
  return str.length > max ? str.slice(0, max) + "..." : str;
}
