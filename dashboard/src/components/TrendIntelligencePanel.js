import React, { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const MONTHS = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"];
const SOURCE_COLORS = ["#2563eb", "#0f766e", "#dc2626", "#9333ea", "#ea580c", "#64748b"];

export function TrendIntelligencePanel({ apiBase }) {
  const [analytics, setAnalytics] = useState({
    companies: [],
    monthly: [],
    seasonal: [],
    velocity: [],
    briefings: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadAnalytics() {
      setLoading(true);
      setError("");
      try {
        const [companiesData, trendsData, velocityData, briefingsData] = await Promise.all([
          fetchJson(`${apiBase}/analytics/companies?limit=20`),
          fetchJson(`${apiBase}/analytics/trends?months=12`),
          fetchJson(`${apiBase}/analytics/velocity?limit=48`),
          fetchJson(`${apiBase}/analytics/briefings?limit=6`),
        ]);

        const monthly = trendsData.monthly || [];
        const hazards = getTopHazards(monthly);
        const seasonalData = await Promise.all(
          hazards.map((hazard) =>
            fetchJson(`${apiBase}/analytics/seasonal/${encodeURIComponent(hazard)}`)
          )
        );

        if (!cancelled) {
          setAnalytics({
            companies: companiesData.companies || [],
            monthly,
            seasonal: seasonalData.map((item) => ({
              hazard: item.hazard_type,
              months: item.seasonal || [],
            })),
            velocity: velocityData.velocity || [],
            briefings: briefingsData.briefings || [],
          });
        }
      } catch (err) {
        console.error("Failed to fetch analytics:", err);
        if (!cancelled) setError("Trend intelligence is not populated yet. Run the weekly analytics pipeline after deploy.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadAnalytics();
    return () => {
      cancelled = true;
    };
  }, [apiBase]);

  const sources = useMemo(() => getTrendSources(analytics.monthly), [analytics.monthly]);
  const latestMonth = analytics.monthly[analytics.monthly.length - 1];

  if (loading) {
    return (
      <section className="trend-panel" aria-label="Trend intelligence">
        <div className="stats-loading" role="status">
          <span className="loading-spinner" aria-hidden="true" />
          Loading trend intelligence...
        </div>
      </section>
    );
  }

  return (
    <section className="trend-panel" aria-label="Trend intelligence">
      <div className="section-heading">
        <p className="eyebrow">Trend intelligence</p>
        <h2>What the recall pattern means</h2>
        <p>
          Phase 4 precomputes company risk, monthly source trends, seasonal hazard baselines,
          resolution velocity, and AI-generated weekly briefings.
        </p>
      </div>

      {error && <p className="analytics-empty">{error}</p>}

      <div className="analytics-grid">
        <article className="analytics-card wide">
          <div className="analytics-card-header">
            <h3>Monthly Recall Trend</h3>
            <span>{analytics.monthly.length} months</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={analytics.monthly}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="SK" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip content={<TrendTooltip />} />
              <Legend />
              <Line type="monotone" dataKey="total_recalls" name="Total" stroke="#111827" strokeWidth={2} dot={false} />
              {sources.map((source, index) => (
                <Line
                  key={source}
                  type="monotone"
                  dataKey={(row) => row.by_source?.[source] || 0}
                  name={source}
                  stroke={SOURCE_COLORS[index % SOURCE_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </article>

        <article className="analytics-card">
          <div className="analytics-card-header">
            <h3>Company Leaderboard</h3>
            <span>Risk score</span>
          </div>
          <div className="company-leaderboard">
            {analytics.companies.slice(0, 8).map((company) => (
              <div key={company.PK} className="leaderboard-row">
                <div>
                  <strong>{company.company_name}</strong>
                  <span>{company.total_recalls} recalls · {company.most_common_hazard || "No hazard label"}</span>
                </div>
                <RiskPill score={company.risk_score} trend={company.trend_direction} />
              </div>
            ))}
            {analytics.companies.length === 0 && <p className="analytics-empty">No company profiles yet.</p>}
          </div>
        </article>

        <article className="analytics-card">
          <div className="analytics-card-header">
            <h3>Resolution Velocity</h3>
            <span>Avg days to close</span>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={buildVelocityChartData(analytics.velocity)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="source" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="avg_days_to_close" name="Avg days" fill="#0f766e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </article>

        <article className="analytics-card wide">
          <div className="analytics-card-header">
            <h3>Seasonal Hazard Heatmap</h3>
            <span>{latestMonth?.SK || "No current month"}</span>
          </div>
          <SeasonalHeatmap seasonal={analytics.seasonal} latestMonth={latestMonth} />
        </article>

        <article className="analytics-card wide">
          <div className="analytics-card-header">
            <h3>Weekly Briefing Archive</h3>
            <span>{analytics.briefings.length} archived</span>
          </div>
          <BriefingArchive briefings={analytics.briefings} />
        </article>
      </div>
    </section>
  );
}

function SeasonalHeatmap({ seasonal, latestMonth }) {
  const currentHazards = useMemo(() => {
    return (latestMonth?.top_hazards || []).reduce((acc, item) => {
      acc[item.type] = item.count;
      return acc;
    }, {});
  }, [latestMonth]);

  if (seasonal.length === 0) {
    return <p className="analytics-empty">Seasonal baselines appear after the weekly analytics job runs.</p>;
  }

  return (
    <div className="seasonal-heatmap">
      <div className="heatmap-header">
        <span>Hazard</span>
        {MONTHS.map((month) => <span key={month}>{month}</span>)}
      </div>
      {seasonal.map((row) => {
        const byMonth = Object.fromEntries(row.months.map((item) => [item.month, item]));
        return (
          <div key={row.hazard} className="heatmap-row">
            <span className="heatmap-label">{row.hazard}</span>
            {MONTHS.map((month) => {
              const cell = byMonth[month];
              const currentCount = latestMonth?.SK?.slice(5, 7) === month ? currentHazards[row.hazard] || 0 : 0;
              const anomalous = cell?.std_dev > 0 && currentCount > cell.avg_count + 2 * cell.std_dev;
              return (
                <span
                  key={month}
                  className={`heatmap-cell ${anomalous ? "anomaly" : ""}`}
                  style={{ "--intensity": Math.min((cell?.avg_count || 0) / 8, 1) }}
                  title={`${row.hazard} month ${month}: avg ${cell?.avg_count || 0}`}
                >
                  {cell?.avg_count || ""}
                </span>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

function BriefingArchive({ briefings }) {
  if (briefings.length === 0) {
    return <p className="analytics-empty">No weekly briefings archived yet.</p>;
  }

  return (
    <div className="briefing-list">
      {briefings.map((briefing) => (
        <article key={briefing.SK} className="briefing-item">
          <div>
            <strong>{briefing.week}</strong>
            <span>{formatDate(briefing.generated_at)} · {briefing.anomaly_count || 0} anomalies</span>
          </div>
          <p>{truncate(stripMarkdown(briefing.briefing_text || ""), 220)}</p>
        </article>
      ))}
    </div>
  );
}

function RiskPill({ score = 0, trend = "insufficient_data" }) {
  return (
    <span className={`risk-pill ${score >= 70 ? "high" : score >= 40 ? "medium" : "low"}`}>
      {score}
      <small>{trend.replace("_", " ")}</small>
    </span>
  );
}

function TrendTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <strong>{label}</strong>
      {payload.map((entry) => (
        <span key={entry.name}>{entry.name}: {entry.value}</span>
      ))}
    </div>
  );
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url} returned ${response.status}`);
  return response.json();
}

function getTopHazards(monthly) {
  const counts = new Map();
  monthly.forEach((month) => {
    (month.top_hazards || []).forEach((hazard) => {
      counts.set(hazard.type, (counts.get(hazard.type) || 0) + hazard.count);
    });
  });
  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([hazard]) => hazard);
}

function getTrendSources(monthly) {
  const sources = new Set();
  monthly.forEach((month) => {
    Object.keys(month.by_source || {}).forEach((source) => sources.add(source));
  });
  return Array.from(sources).slice(0, 5);
}

function buildVelocityChartData(velocity) {
  const latestBySource = new Map();
  velocity.forEach((item) => {
    const current = latestBySource.get(item.source);
    if (!current || item.quarter > current.quarter) {
      latestBySource.set(item.source, item);
    }
  });
  return Array.from(latestBySource.values()).sort((a, b) => a.source.localeCompare(b.source));
}

function formatDate(value) {
  if (!value) return "Unknown date";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

function stripMarkdown(value) {
  return value.replace(/[#*_`]/g, "").trim();
}

function truncate(value, maxLength) {
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value;
}
