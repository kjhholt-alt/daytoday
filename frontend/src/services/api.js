import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status } = error.response;
      if (status === 401) {
        console.warn('Authentication required. Please log in.');
      }
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
export const getAuthStatus = () => api.get('/auth/status/');
export const triggerLogin = () => api.post('/auth/login/');
export const triggerLogout = () => api.post('/auth/logout/');

export default api;
