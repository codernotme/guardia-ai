"use client";

import React from "react";
import { Tooltip } from "@heroui/react";

interface GcsTooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function GcsTooltip({ content, children, className }: GcsTooltipProps) {
  if (!content) return <>{children}</>;
  return (
    <Tooltip delay={200}>
      <Tooltip.Trigger className={className}>{children}</Tooltip.Trigger>
      <Tooltip.Content className="px-2 py-1 text-xs rounded-md bg-default-800 text-default-foreground shadow-lg border border-border/40 z-50">
        {content}
      </Tooltip.Content>
    </Tooltip>
  );
}

export default GcsTooltip;
