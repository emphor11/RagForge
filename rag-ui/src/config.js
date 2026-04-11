// This allows the app to use your local backend during development 
// and your Render backend in production.
export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
