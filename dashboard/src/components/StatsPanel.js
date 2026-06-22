import React, { useMemo, useState } from "react";
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

const CLASS_LABELS = {
  "Class I": "High Risk",
  "Class II": "Medium Risk",
  "Class III": "Low Risk",
};

const FIRM_RANKING_MODES = {
  count: {
    label: "Most Recalls",
    metricLabel: "Recalls",
  },
  severity: {
    label: "Highest Risk",
    metricLabel: "Severity Score",
  },
};

export function StatsPanel({ stats, recalls = [], loading }) {
  const [firmRankingMode, setFirmRankingMode] = useState("count");
  const firmDetails = useMemo(() => buildFirmDetails(recalls), [recalls]);
  const firmData = useMemo(
    () => buildFirmData(stats, firmDetails, firmRankingMode),
    [firmDetails, firmRankingMode, stats]
  );
  const metricLabel = FIRM_RANKING_MODES[firmRankingMode].metricLabel;

  if (loading || !stats) {
    return (
      <div className="stats-loading" role="status">
        <span className="loading-spinner" aria-hidden="true" />
        Loading recall snapshot...
      </div>
    );
  }

  const classData = Object.entries(stats.by_classification || {}).map(
    ([name, value]) => ({ name, value })
  );
  const classTotal = classData.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="stats-panel">
      <p className="eyebrow">Quick context</p>
      <h2>Recall Snapshot</h2>

      <div className="stat-cards">
        <div className="stat-card">
          <span className="stat-number">
            {stats.total_recalls?.toLocaleString()}
          </span>
          <span className="stat-label">Recent recalls</span>
        </div>
        <div className="stat-card">
          <span className="stat-number">
            {stats.by_classification?.["Class I"] || 0}
          </span>
          <span className="stat-label critical">High-risk recalls</span>
        </div>
        <div className="stat-card">
          <span className="stat-number">{stats.nationwide_percentage}%</span>
          <span
            className="stat-label"
            title="Percentage of recalls distributed across all 50 states."
          >
            Nationwide recalls
          </span>
        </div>
      </div>

      <div className="source-breakdown">
        <h3>By Agency</h3>
        {Object.entries(stats.by_source || {})
          .sort(([, a], [, b]) => b - a)
          .map(([source, count]) => (
            <div key={source} className="breakdown-row">
              <span>{source.replace(/_/g, " ")}</span>
              <strong>{count.toLocaleString()}</strong>
            </div>
          ))}
      </div>

      <div className="source-breakdown">
        <h3>By Category</h3>
        {Object.entries(stats.by_category || {})
          .sort(([, a], [, b]) => b - a)
          .map(([category, count]) => (
            <div key={category} className="breakdown-row">
              <span>{category.replace(/_/g, " ")}</span>
              <strong>{count.toLocaleString()}</strong>
            </div>
          ))}
      </div>

      <div className="classification-summary">
        <div className="classification-summary-header">
          <h3>Risk Mix Across Visible Recalls</h3>
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
                title={`${CLASS_LABELS[entry.name] || entry.name}: ${entry.value.toLocaleString()}`}
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
              {CLASS_LABELS[entry.name] || entry.name}: {entry.value.toLocaleString()}
            </span>
          ))}
        </div>
      </div>

      <div className="top-firms-header">
        <h3>Companies With Recent Recalls</h3>
        <div className="segmented-control" aria-label="Top firms ranking mode">
          {Object.entries(FIRM_RANKING_MODES).map(([mode, config]) => (
            <button
              key={mode}
              type="button"
              className={firmRankingMode === mode ? "active" : ""}
              onClick={() => setFirmRankingMode(mode)}
              aria-pressed={firmRankingMode === mode}
            >
              {config.label}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={190}>
        <BarChart data={firmData} layout="vertical">
          <XAxis
            type="number"
            tick={{ fontSize: 10 }}
            label={{
              value: metricLabel,
              position: "insideBottom",
              offset: -2,
            }}
            height={34}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={100}
            tick={{ fontSize: 11 }}
          />
          <Tooltip content={<FirmTooltip metricLabel={metricLabel} />} />
          <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function FirmTooltip({ active, payload, metricLabel }) {
  if (!active || !payload?.length) return null;

  const firm = payload[0].payload;
  const details = firm.details;

  return (
    <div className="chart-tooltip">
      <strong>{firm.fullName}</strong>
      <span>
        {firm.value.toLocaleString()} {metricLabel.toLowerCase()}
      </span>
      <span>{firm.totalRecalls.toLocaleString()} total recalls</span>
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

function buildFirmData(stats, firmDetails, firmRankingMode) {
  if (!stats) return [];

  if (firmRankingMode === "severity") {
    return (stats.top_firms_by_severity || []).slice(0, 5).map((firm) => ({
      name: truncateFirmName(firm.firm),
      fullName: firm.firm,
      value: firm.severity_score,
      totalRecalls: firm.total_recalls,
      details: firmDetails[firm.firm] || buildTooltipDetails(firm.by_classification),
    }));
  }

  return Object.entries(stats.top_firms || {})
    .slice(0, 5)
    .map(([name, value]) => ({
      name: truncateFirmName(name),
      fullName: name,
      value,
      totalRecalls: value,
      details: firmDetails[name],
    }));
}

function buildTooltipDetails(classifications = {}) {
  return {
    classifications: {
      "Class I": classifications["Class I"] || 0,
      "Class II": classifications["Class II"] || 0,
      "Class III": classifications["Class III"] || 0,
    },
    states: [],
    products: [],
  };
}

function buildFirmDetails(recalls) {
  const details = recalls.reduce((acc, recall) => {
    const firmName = recall.recalling_firm || recall.company || "Unknown";
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
    (recall.affected_states || recall.states || []).forEach((state) => firm.states.add(state));
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

function truncateFirmName(name) {
  return name.length > 20 ? name.slice(0, 18) + "..." : name;
}

function truncate(str, max) {
  return str.length > max ? str.slice(0, max) + "..." : str;
}
