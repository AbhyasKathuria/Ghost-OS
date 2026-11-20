import React from "react";
import type { ModuleCompatibility } from "../types";

interface CompatibilityBadgeProps {
  module: string;
  status: ModuleCompatibility;
}

export const CompatibilityBadge: React.FC<CompatibilityBadgeProps> = ({ module, status }) => {
  const getBadgeStyle = (st: ModuleCompatibility) => {
    switch (st) {
      case "supported":
        return "bg-red-950/60 text-white border-red-600/70 shadow-sm shadow-red-950/50";
      case "limited":
        return "bg-zinc-900 text-zinc-300 border-zinc-700";
      case "permission_denied":
        return "bg-red-950 text-red-400 border-red-600";
      case "unsupported":
      default:
        return "bg-black text-zinc-500 border-zinc-800";
    }
  };

  const getLabel = (st: ModuleCompatibility) => {
    switch (st) {
      case "supported":
        return "Supported";
      case "limited":
        return "Limited";
      case "permission_denied":
        return "Root Required";
      case "unsupported":
        return "Unsupported";
    }
  };

  return (
    <div className="flex items-center justify-between p-2 rounded bg-zinc-950 border border-zinc-800">
      <span className="text-xs font-semibold text-zinc-200 uppercase tracking-wider">{module}</span>
      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${getBadgeStyle(status)}`}>
        {getLabel(status)}
      </span>
    </div>
  );
};
