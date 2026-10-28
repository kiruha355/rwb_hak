// One palette for every chart: graphite and silver, ice blue only for "look here".
export const C = {
  ink: "#1f2226",
  silver: "#c3c8cf",
  ice: "#63b3e3",
  iceSoft: "#d9ebf7",
  sand: "#d9c4a3",
  grid: "#eceef1",
};

export const tip = {
  contentStyle: { background: "#ffffff", border: "none", borderRadius: 16, fontSize: 13, boxShadow: "0 12px 32px rgba(0,0,0,.10)", padding: "10px 14px" },
  labelStyle: { color: "#6b717b", fontWeight: 500 },
  cursor: { fill: "rgba(23,25,29,0.04)" },
};
export const axis = { stroke: "#9aa0a8", fontSize: 12, tickLine: false, axisLine: false } as const;
