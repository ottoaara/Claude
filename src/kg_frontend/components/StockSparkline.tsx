"use client";

interface PricePoint {
  date: string | null;
  close: number | null;
}

interface StockData {
  before: PricePoint;
  on:     PricePoint;
  after:  PricePoint;
  change_pct: number | null;
  color: "red" | "green" | "black" | "gray";
}

interface Props {
  data: StockData;
  width?: number;
  height?: number;
}

const COLOR_MAP = {
  red:   "#dc2626",
  green: "#16a34a",
  black: "#1f2937",
  gray:  "#9ca3af",
};

export default function StockSparkline({ data, width = 96, height = 40 }: Props) {
  const points = [data.before, data.on, data.after];
  const closes = points.map((p) => p.close).filter((v): v is number => v !== null);

  if (closes.length < 2) {
    return (
      <div
        style={{ width, height }}
        className="flex items-center justify-center text-xs text-gray-400"
      >
        N/A
      </div>
    );
  }

  const minV = Math.min(...closes);
  const maxV = Math.max(...closes);
  const range = maxV - minV || 1;

  const pad = 4;
  const usableW = width  - pad * 2;
  const usableH = height - pad * 2;

  // Map each point to SVG coordinates
  const coords: Array<[number, number] | null> = points.map((p, i) => {
    if (p.close === null) return null;
    const x = pad + (i / (points.length - 1)) * usableW;
    const y = pad + usableH - ((p.close - minV) / range) * usableH;
    return [x, y];
  });

  // Build polyline path from non-null points
  const validCoords = coords.filter((c): c is [number, number] => c !== null);
  const pathD = validCoords.map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x} ${y}`).join(" ");

  const stroke = COLOR_MAP[data.color] ?? COLOR_MAP.gray;
  const changePct = data.change_pct;

  return (
    <div className="flex flex-col items-center gap-0.5">
      <svg width={width} height={height} className="overflow-visible">
        {/* Zero-change reference line (midpoint) */}
        <line
          x1={pad} y1={pad + usableH / 2}
          x2={width - pad} y2={pad + usableH / 2}
          stroke="#e5e7eb" strokeWidth="1" strokeDasharray="2,2"
        />
        {/* Price line */}
        <path
          d={pathD}
          fill="none"
          stroke={stroke}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Dots at each point */}
        {validCoords.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="2.5" fill={stroke} />
        ))}
      </svg>
      {/* Change label */}
      {changePct !== null && (
        <span
          className="text-xs font-bold leading-none"
          style={{ color: stroke }}
        >
          {changePct > 0 ? "+" : ""}{changePct.toFixed(1)}%
        </span>
      )}
    </div>
  );
}
