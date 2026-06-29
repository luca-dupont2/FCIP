export const API_URL = import.meta.env.VITE_API_URL || '/api';

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return 'N/A';
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return 'N/A';
  return `${(value * 100).toFixed(1)}%`;
}

export function formatWns(wns: number | null | undefined): { text: string; color: string } {
  if (wns == null) return { text: 'N/A', color: 'gray' };
  if (wns >= 0) return { text: wns.toFixed(3), color: 'green' };
  if (wns >= -0.5) return { text: wns.toFixed(3), color: 'yellow' };
  return { text: wns.toFixed(3), color: 'red' };
}

export function utilizationColor(pct: number | null | undefined): string {
  if (pct == null) return 'gray';
  if (pct > 0.95) return 'red';
  if (pct > 0.80) return 'orange';
  return 'green';
}
