// frontend/src/utils/formatTime.js
//
// Shared time-formatting helpers — used by SupportSidebar (history
// timestamps) and the Admin Engineers tab (last login, total time),
// pulled out to one place instead of being duplicated in both.

function parseServerTime(isoString) {
  if (!isoString) return null;

  // New backend timestamps include an explicit UTC offset. Historical
  // Render records were UTC but had no suffix, so browsers interpreted
  // them as local time and displayed roughly "6h ago" in India.
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(isoString);
  const normalized = hasTimezone ? isoString : `${isoString}Z`;
  const parsed = new Date(normalized);

  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function formatRelativeTime(isoString) {
  const parsed = parseServerTime(isoString);
  if (!parsed) return "";

  const then = parsed.getTime();
  if (Number.isNaN(then)) return "";

  const diffMin = Math.max(
    0,
    Math.floor((Date.now() - then) / 60000)
  );
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;

  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;

  const diffDay = Math.round(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;

  return parsed.toLocaleDateString();
}

export function formatDuration(totalMinutes) {
  if (!totalMinutes) return "—";

  const hours = Math.floor(totalMinutes / 60);
  const minutes = Math.round(totalMinutes % 60);

  if (hours === 0) return `${minutes}m`;
  return `${hours}h ${minutes}m`;
}
