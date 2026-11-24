// Where the Flask backend lives. For local development this is the default;
// when deploying, set VITE_API_BASE (see .env.example) instead of editing code.
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000'

// Photo URLs from the backend use its access-checked /api/photos/... route.
export function resolvePhotoUrl(url) {
  if (!url) return null
  return url.startsWith('http') ? url : `${API_BASE}${url}`
}
