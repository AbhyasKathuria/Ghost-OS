import React from "react";

interface HealthGaugeProps {
  score: number;
  size?: "sm" | "md" | "lg";
  label?: string;
}

export const HealthGauge: React.FC<HealthGaugeProps> = ({ score, size = "md", label }) => {
  const getColor = (s: number) => {
    if (s >= 85) return { stroke: "#EF4444", text: "text-white", bg: "bg-red-950/40", border: "border-red-600/60" };
    if (s >= 70) return { stroke: "#DC2626", text: "text-red-300", bg: "bg-red-950/60", border: "border-red-700/60" };
    return { stroke: "#991B1B", text: "text-red-500", bg: "bg-red-950/80", border: "border-red-800" };
  };

  const colors = getColor(score);
  const strokeWidth = size === "sm" ? 6 : size === "md" ? 8 : 10;
  const radius = size === "sm" ? 22 : size === "md" ? 36 : 48;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const svgSize = (radius + strokeWidth) * 2;

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative flex items-center justify-center">
        <svg width={svgSize} height={svgSize} className="transform -rotate-90">
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            stroke="#27272A"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            stroke={colors.stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            fill="transparent"
            className="transition-all duration-700 ease-out"
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center">
          <span className={`font-mono font-black ${size === "sm" ? "text-xs" : size === "md" ? "text-lg" : "text-2xl"} ${colors.text}`}>
            {score}
          </span>
          {size !== "sm" && <span className="text-[10px] text-zinc-400 font-bold">/100</span>}
        </div>
      </div>
      {label && <span className="mt-1.5 text-xs text-zinc-300 font-medium text-center">{label}</span>}
    </div>
  );
};
