import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const CLASS_COLORS = {
  "Class I": "#dc2626",
  "Class II": "#ea580c",
  "Class III": "#ca8a04",
};

export function StatsPanel({ stats, loading }) {
  if (loading || !stats) {
    return <div className="stats-loading">Loading stats...</div>;
  }

  const classData = Object.entries(stats.by_classification || {}).map(
    ([name, value]) => ({ name, value })
  );

  const firmData = Object.entries(stats.top_firms || {})
    .slice(0, 5)
    .map(([name, value]) => ({
      name: name.length > 20 ? name.slice(0, 18) + "..." : name,
      value,
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
          <span className="stat-label">Nationwide</span>
        </div>
      </div>

      <h3>By Classification</h3>
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={classData} layout="vertical">
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="name"
            width={60}
            tick={{ fontSize: 12 }}
          />
          <Tooltip />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {classData.map((entry) => (
              <Cell
                key={entry.name}
                fill={CLASS_COLORS[entry.name] || "#888"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

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
          <Tooltip />
          <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
