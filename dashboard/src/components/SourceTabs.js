import React from "react";

const SOURCES = [
  { key: "all", label: "All Sources" },
  { key: "FDA_FOOD", label: "FDA Food" },
  { key: "FDA_DRUG", label: "FDA Drugs" },
  { key: "FDA_DEVICE", label: "FDA Devices" },
  { key: "CPSC", label: "Consumer Products" },
  { key: "USDA", label: "USDA Meat/Poultry" },
  { key: "NHTSA", label: "Vehicles" },
];

export function SourceTabs({ activeSource, onSourceChange, counts = {} }) {
  return (
    <nav className="source-tabs" aria-label="Recall source">
      {SOURCES.map((source) => (
        <button
          key={source.key}
          type="button"
          className={`source-tab ${activeSource === source.key ? "active" : ""}`}
          onClick={() => onSourceChange(source.key)}
          aria-pressed={activeSource === source.key}
        >
          <span>{source.label}</span>
          {source.key !== "all" && counts[source.key] !== undefined && (
            <span className="source-count">{counts[source.key].toLocaleString()}</span>
          )}
        </button>
      ))}
    </nav>
  );
}
