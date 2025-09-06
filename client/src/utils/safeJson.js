export function safeJsonParse(s, fallback = {}) {
  try { return JSON.parse(s) } catch { return fallback }
}