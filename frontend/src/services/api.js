import axios from 'axios';

// Use relative URL so it works both in dev (proxy) and production (same origin)
const api = axios.create({
  baseURL: window.location.port === '3000'
    ? 'http://localhost:8000/api'  // Dev mode: React dev server proxies to Django
    : '/api',                       // Production: served from same origin
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status } = error.response;
      if (status >= 500) {
        console.error('Server error:', error.response.data);
      }
    } else if (error.request) {
      console.error('Network error: Backend may not be running.');
    }
    return Promise.reject(error);
  }
);

export const getToday = () => api.get('/summaries/today/');
export const getByDate = (date) => api.get(`/summaries/by-date/${date}/`);
export const getHistory = (page = 1) => api.get(`/summaries/?page=${page}`);
export const search = (query) => api.get(`/search/?q=${encodeURIComponent(query)}`);
export const triggerCollection = (date) => api.post('/collect/', { date });
export const getStatus = () => api.get('/status/');

// Config
export const saveConfig = (data) => api.post('/config/', data);

// Notes
export const openNote = (noteId) => api.post(`/notes/${noteId}/open/`);

// Calendar import (Power Automate)
export const getCalendarImportStatus = () => api.get('/calendar/import/');
export const importCalendarEvents = (events, date) => api.post('/calendar/import/', { events, date });
export const bulkImportCalendar = () => api.post('/calendar/bulk-import/', {}, { timeout: 300000 });

// Attendees
export const searchAttendees = (query) => api.get(`/attendees/?q=${encodeURIComponent(query)}`);
export const getTopAttendees = (limit = 20) => api.get(`/attendees/top/?limit=${limit}`);

