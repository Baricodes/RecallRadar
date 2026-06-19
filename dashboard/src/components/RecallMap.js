import React, { useMemo, useState } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
} from "react-simple-maps";
import { scaleQuantize } from "d3-scale";

const GEO_URL = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

const CLASS_COLORS = {
  "Class I": "#dc2626",
  "Class II": "#ea580c",
  "Class III": "#ca8a04",
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

export function RecallMap({ stats, recalls = [], selectedState, onStateClick }) {
  const [tooltip, setTooltip] = useState(null);
  const stateCounts = useMemo(
    () => stats?.state_counts || stats?.top_states || {},
    [stats]
  );
  const maxCount = Math.max(...Object.values(stateCounts), 0);

  const stateClassCounts = useMemo(() => {
    return recalls.reduce((acc, recall) => {
      const states = recall.affected_states || [];
      states.forEach((state) => {
        if (!acc[state]) {
          acc[state] = { ...EMPTY_BREAKDOWN };
        }
        acc[state][recall.classification] =
          (acc[state][recall.classification] || 0) + 1;
      });
      return acc;
    }, {});
  }, [recalls]);

  const colorScale = useMemo(() => {
    if (!stateCounts || Object.keys(stateCounts).length === 0) {
      return () => "#EEE";
    }
    const values = Object.values(stateCounts);
    const max = Math.max(...values, 1);
    return scaleQuantize()
      .domain([0, max])
      .range([
        "#fee5d9", "#fcbba1", "#fc9272",
        "#fb6a4a", "#ef3b2c", "#cb181d", "#99000d",
      ]);
  }, [stateCounts]);

  return (
    <div className="recall-map">
      <ComposableMap projection="geoAlbersUsa">
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map((geo) => {
              const stateCode = FIPS_TO_STATE[geo.id];
              const count = stateCounts[stateCode] || 0;
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
                      count,
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
                      fill: isSelected ? "#2563eb" : colorScale(count),
                      stroke: "#fff",
                      strokeWidth: 0.5,
                      outline: "none",
                    },
                    hover: {
                      fill: "#3b82f6",
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

      <div className="map-legend" aria-label="Recall activity color scale">
        <div className="legend-scale" />
        <div className="legend-labels">
          <span>0</span>
          <span>{maxCount.toLocaleString()}</span>
        </div>
        <div className="legend-caption">Low to high recall activity</div>
      </div>

      {tooltip && (
        <div
          className="map-tooltip"
          style={{ left: tooltip.x + 14, top: tooltip.y + 14 }}
        >
          <strong>
            {tooltip.stateName} ({tooltip.stateCode})
          </strong>
          <span>{tooltip.count.toLocaleString()} total recalls</span>
          <div className="tooltip-breakdown">
            {Object.entries(CLASS_COLORS).map(([classification, color]) => (
              <span key={classification} style={{ color }}>
                {classification}: {tooltip.breakdown[classification] || 0}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
