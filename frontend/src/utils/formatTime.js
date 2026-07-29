// frontend/src/utils/formatTime.js
//
// Shared time-formatting helpers — used by SupportSidebar (history
// timestamps) and the Admin Engineers tab (last login, total time),
// pulled out to one place instead of being duplicated in both.

export function formatRelativeTime(isoString) {
  const then = new Date(isoString).getTime();
  if (Number.isNaN(then)) return "";

  const diffMin = Math.round((Date.now() - then) / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;

  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;

  const diffDay = Math.round(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;

  return new Date(isoString).toLocaleDateString();
}

export function formatDuration(totalMinutes) {
  if (!totalMinutes) return "—";

  const hours = Math.floor(totalMinutes / 60);
  const minutes = Math.round(totalMinutes % 60);

  if (hours === 0) return `${minutes}m`;
  return `${hours}h ${minutes}m`;
}