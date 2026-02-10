import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import DailySummary from './pages/DailySummary';
import History from './pages/History';
import Search from './pages/Search';
import Settings from './pages/Settings';

const theme = createTheme({
  palette: {
    primary: { main: '#1565c0' },
    secondary: { main: '#00838f' },
  },
  typography: {
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <ErrorBoundary>
        <BrowserRouter>
          <Layout>
            <Routes>
              <Route path="/" element={<DailySummary />} />
              <Route path="/day/:date" element={<DailySummary />} />
              <Route path="/history" element={<History />} />
              <Route path="/search" element={<Search />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Layout>
        </BrowserRouter>
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default App;
