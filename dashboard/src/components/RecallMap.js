import React, { useMemo } from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
} from "react-simple-maps";
import { scaleQuantize } from "d3-scale";

const GEO_URL = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

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

export function RecallMap({ stats, selectedState, onStateClick }) {
  const stateCounts = stats?.state_counts || stats?.top_states || {};

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
    <ComposableMap projection="geoAlbersUsa">
      <Geographies geography={GEO_URL}>
        {({ geographies }) =>
          geographies.map((geo) => {
            const stateCode = FIPS_TO_STATE[geo.id];
            const count = stateCounts[stateCode] || 0;
            const isSelected = selectedState === stateCode;

            return (
              <Geography
                key={geo.rsmKey}
                geography={geo}
                onClick={() => onStateClick(stateCode)}
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
  );
}
