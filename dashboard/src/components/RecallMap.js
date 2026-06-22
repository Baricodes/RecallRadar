import React, { useMemo, useState } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
} from "react-simple-maps";
import { scaleQuantize } from "d3-scale";
import {
  interpolateCividis,
  interpolateReds,
  interpolateViridis,
} from "d3-scale-chromatic";

const GEO_URL = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";
const getColorStops = (interpolator) =>
  Array.from({ length: 7 }, (_, index) => interpolator(index / 6));

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

const CLASS_WEIGHTS = {
  "Class I": 3,
  "Class II": 2,
  "Class III": 1,
};

const MAP_MODES = {
  volume: {
    label: "Volume",
    metricLabel: "total recalls",
    legendCaption: "Recall volume by state",
    colorStops: getColorStops(interpolateViridis),
    selectedColor: "#2563eb",
    hoverColor: "#3b82f6",
  },
  riskScore: {
    label: "Risk Score",
    metricLabel: "risk score",
    legendCaption: "Weighted recall risk by state",
    colorStops: getColorStops(interpolateCividis),
    selectedColor: "#6f5f00",
    hoverColor: "#9c8500",
  },
  classI: {
    label: "Class I Only",
    metricLabel: "high-risk recalls",
    legendCaption: "High-risk recall volume by state",
    colorStops: getColorStops(interpolateReds),
    selectedColor: "#b91c1c",
    hoverColor: "#ef4444",
  },
};

const FIPS_TO_STATE = {
  "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
  "08": "CO", "09": "CT", "10": "DE", "12": "FL", "13": "GA",
  "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA",
  "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
  "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO",
  "30": "MT", "31": "NE", "32": "NV", "33": "NH", "34": "NJ",
  "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
  "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC",
  "46": "SD", "47": "TN", "48": "TX", "49": "UT", "50": "VT",
  "51": "VA", "53": "WA", "54": "WV", "55": "WI", "56": "WY",
  "11": "DC",
};

const EMPTY_BREAKDOWN = {
  "Class I": 0,
  "Class II": 0,
  "Class III": 0,
};

export function RecallMap({ stats, selectedState, onStateClick }) {
  const [tooltip, setTooltip] = useState(null);
  const [mapMode, setMapMode] = useState("volume");
  const stateCounts = useMemo(
    () => stats?.state_counts || stats?.top_states || {},
    [stats]
  );
  const stateClassCounts = useMemo(
    () => stats?.state_class_counts || {},
    [stats]
  );

  const stateMetrics = useMemo(() => {
    if (mapMode === "volume") {
      return stateCounts;
    }

    return Object.fromEntries(
      Object.entries(stateClassCounts).map(([stateCode, breakdown]) => {
        if (mapMode === "classI") {
          return [stateCode, breakdown["Class I"] || 0];
        }

        const riskScore = Object.entries(CLASS_WEIGHTS).reduce(
          (score, [classification, weight]) =>
            score + (breakdown[classification] || 0) * weight,
          0
        );
        return [stateCode, riskScore];
      })
    );
  }, [mapMode, stateClassCounts, stateCounts]);

  const modeConfig = MAP_MODES[mapMode];
  const mapColorStops = modeConfig.colorStops;
  const maxMetric = Math.max(...Object.values(stateMetrics), 0);

  const colorScale = useMemo(() => {
    if (!stateMetrics || Object.keys(stateMetrics).length === 0) {
      return () => "#EEE";
    }
    const values = Object.values(stateMetrics);
    const max = Math.max(...values, 1);
    return scaleQuantize()
      .domain([0, max])
      .range(mapColorStops);
  }, [mapColorStops, stateMetrics]);

  return (
    <div
      className="recall-map"
      style={{ "--map-active-color": modeConfig.selectedColor }}
    >
      <div className="map-controls">
        <span>Map view</span>
        <div className="segmented-control" aria-label="Map metric">
          {Object.entries(MAP_MODES).map(([mode, config]) => (
            <button
              key={mode}
              type="button"
              className={mapMode === mode ? "active" : ""}
              onClick={() => setMapMode(mode)}
              aria-pressed={mapMode === mode}
            >
              {config.label}
            </button>
          ))}
        </div>
      </div>

      <ComposableMap projection="geoAlbersUsa">
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map((geo) => {
              const stateCode = FIPS_TO_STATE[geo.id];
              const metricValue = stateMetrics[stateCode] || 0;
              const isSelected = selectedState === stateCode;
              const breakdown = stateClassCounts[stateCode] || EMPTY_BREAKDOWN;

              return (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  onClick={() => stateCode && onStateClick(stateCode)}
                  onMouseEnter={(event) =>
                    setTooltip({
                      x: event.clientX,
                      y: event.clientY,
                      stateCode,
                      stateName: geo.properties.name,
                      metricValue,
                      breakdown,
                    })
                  }
                  onMouseMove={(event) =>
                    setTooltip((current) =>
                      current
                        ? { ...current, x: event.clientX, y: event.clientY }
                        : current
                    )
                  }
                  onMouseLeave={() => setTooltip(null)}
                  style={{
                    default: {
                      fill: isSelected
                        ? modeConfig.selectedColor
                        : colorScale(metricValue),
                      stroke: "#fff",
                      strokeWidth: 0.5,
                      outline: "none",
                    },
                    hover: {
                      fill: modeConfig.hoverColor,
                      stroke: "#fff",
                      strokeWidth: 1,
                      outline: "none",
                      cursor: "pointer",
                    },
                    pressed: { outline: "none" },
                  }}
                />
              );
            })
          }
        </Geographies>
      </ComposableMap>

      <div
        className="map-legend"
        aria-label={`${modeConfig.legendCaption} color scale`}
      >
        <div
          className="legend-scale"
          style={{
            background: `linear-gradient(90deg, ${mapColorStops.join(", ")})`,
          }}
        />
        <div className="legend-labels">
          <span>0</span>
          <span>{maxMetric.toLocaleString()}</span>
        </div>
        <div className="legend-caption">{modeConfig.legendCaption}</div>
      </div>

      {tooltip && (
        <div
          className="map-tooltip"
          style={{ left: tooltip.x + 14, top: tooltip.y + 14 }}
        >
          <strong>
            {tooltip.stateName} ({tooltip.stateCode})
          </strong>
          <span>
            {tooltip.metricValue.toLocaleString()} {modeConfig.metricLabel}
          </span>
          <div className="tooltip-breakdown">
            {Object.entries(CLASS_COLORS).map(([classification, color]) => (
              <span key={classification} style={{ color }}>
                {CLASS_LABELS[classification]}: {tooltip.breakdown[classification] || 0}
              </span>
            ))}
          </div>
          <span className="tooltip-hint">Click to show recalls in this state.</span>
        </div>
      )}
    </div>
  );
}
