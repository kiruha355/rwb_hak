// One palette for every chart: graphite for the main series, blue for "look here", sand for the comparison.
export const C = {
  ink: "#1f2226",
  accent: "#2f7fb8",
  accentSoft: "#a9cbe4",
  silver: "#c6cbd2",
  sand: "#c99a6b",
  grid: "#eceef1",
};

export const tip = {
  contentStyle: { background: "#ffffff", border: "1px solid #e3e6ea", borderRadius: 6, fontSize: 12.5, boxShadow: "0 4px 14px rgba(0,0,0,.08)", padding: "8px 10px" },
  labelStyle: { color: "#5f6670", fontWeight: 500, marginBottom: 2 },
  cursor: { fill: "rgba(31,34,38,0.04)" },
};
export const axis = { stroke: "#8b929c", fontSize: 11.5, tickLine: false, axisLine: false } as const;
