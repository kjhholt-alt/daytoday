import React, { useState, useMemo } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import DailySummary from './pages/DailySummary';
import History from './pages/History';
import Search from './pages/Search';
import Settings from './pages/Settings';
import People from './pages/People';
import ThemeContext from './ThemeContext';

function getInitialDarkMode() {
  const stored = localStorage.getItem('darkMode');
  if (stored !== null) {
    return stored === 'true';
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function App() {
  const [darkMode, setDarkMode] = useState(getInitialDarkMode);

  const toggleDarkMode = () => {
    setDarkMode((prev) => {
      const next = !prev;
      localStorage.setItem('darkMode', String(next));
      return next;
    });
  };

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode: darkMode ? 'dark' : 'light',
          primary: { main: '#1565c0' },
          secondary: { main: '#00838f' },
          ...(darkMode && {
            background: {
              default: '#121212',
              paper: '#1e1e1e',
            },
          }),
        },
        typography: {
          h5: { fontWeight: 600 },
          h6: { fontWeight: 600 },
        },
      }),
    [darkMode],
  );

  return (
    <ThemeContext.Provider value={{ darkMode, toggleDarkMode }}>
      <ThemeProvider theme={theme}>
        <ErrorBoundary>
          <BrowserRouter>
            <Layout>
              <Routes>
                <Route path="/" element={<DailySummary />} />
                <Route path="/day/:date" element={<DailySummary />} />
                <Route path="/history" element={<History />} />
                <Route path="/search" element={<Search />} />
                <Route path="/people" element={<People />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </Layout>
          </BrowserRouter>
        </ErrorBoundary>
      </ThemeProvider>
    </ThemeContext.Provider>
  );
}

export default App;
