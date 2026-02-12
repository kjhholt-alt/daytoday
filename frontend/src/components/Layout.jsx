import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AppBar,
  Box,
  CssBaseline,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Button,
  Snackbar,
  Alert,
  Tooltip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Today as TodayIcon,
  History as HistoryIcon,
  Search as SearchIcon,
  Group as PeopleIcon,
  Settings as SettingsIcon,
  Refresh as RefreshIcon,
  Brightness4 as Brightness4Icon,
  Brightness7 as Brightness7Icon,
  TrendingUp as TrendingUpIcon,
} from '@mui/icons-material';
import { triggerCollection } from '../services/api';
import { useThemeContext } from '../ThemeContext';

const drawerWidth = 240;

const navItems = [
  { text: 'Today', icon: <TodayIcon />, path: '/' },
  { text: 'Weekly Recap', icon: <TrendingUpIcon />, path: '/weekly' },
  { text: 'History', icon: <HistoryIcon />, path: '/history' },
  { text: 'Search', icon: <SearchIcon />, path: '/search' },
  { text: 'People', icon: <PeopleIcon />, path: '/people' },
  { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
];

export default function Layout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });
  const { darkMode, toggleDarkMode } = useThemeContext();

  // Keyboard shortcut: Ctrl+K / Cmd+K to focus search
  const handleKeyDown = useCallback((e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      navigate('/search');
    }
  }, [navigate]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const handleCollect = async () => {
    setCollecting(true);
    try {
      await triggerCollection();
      setSnackbar({
        open: true,
        message: 'Data collection complete!',
        severity: 'success',
      });
      if (location.pathname === '/') {
        window.location.reload();
      }
    } catch (err) {
      const detail = err.response?.data?.detail || 'Collection failed. Check backend logs.';
      setSnackbar({ open: true, message: detail, severity: 'error' });
    } finally {
      setCollecting(false);
    }
  };

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          DayToDay
        </Typography>
      </Toolbar>
      <List>
        {navItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => {
                navigate(item.path);
                setMobileOpen(false);
              }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{ width: { sm: `calc(100% - ${drawerWidth}px)` }, ml: { sm: `${drawerWidth}px` } }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={() => setMobileOpen(!mobileOpen)}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {navItems.find((i) => i.path === location.pathname)?.text || 'DayToDay'}
          </Typography>
          <Tooltip title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}>
            <IconButton color="inherit" onClick={toggleDarkMode} sx={{ mr: 1 }}>
              {darkMode ? <Brightness7Icon /> : <Brightness4Icon />}
            </IconButton>
          </Tooltip>
          <Button
            color="inherit"
            startIcon={<RefreshIcon />}
            onClick={handleCollect}
            disabled={collecting}
          >
            {collecting ? 'Collecting...' : 'Run Collection'}
          </Button>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          mt: 8,
        }}
      >
        {children}
      </Box>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={5000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
      >
        <Alert
          severity={snackbar.severity}
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
