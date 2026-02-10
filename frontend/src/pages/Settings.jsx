import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Stack,
  Paper,
  Button,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  AccountCircle as AccountIcon,
  Login as LoginIcon,
  Logout as LogoutIcon,
  Folder as FolderIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { getAuthStatus, triggerLogin, triggerLogout } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';

export default function Settings() {
  const [authStatus, setAuthStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const fetchAuth = async () => {
    try {
      const res = await getAuthStatus();
      setAuthStatus(res.data);
    } catch (err) {
      setAuthStatus({ authenticated: false, error: 'Backend not reachable.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuth();
  }, []);

  const handleLogin = async () => {
    setActionLoading(true);
    setMessage(null);
    try {
      await triggerLogin();
      await fetchAuth();
      setMessage({ text: 'Logged in successfully!', severity: 'success' });
    } catch (err) {
      setMessage({
        text: err.response?.data?.detail || 'Login failed.',
        severity: 'error',
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleLogout = async () => {
    setActionLoading(true);
    setMessage(null);
    try {
      await triggerLogout();
      await fetchAuth();
      setMessage({ text: 'Logged out.', severity: 'info' });
    } catch (err) {
      setMessage({
        text: err.response?.data?.detail || 'Logout failed.',
        severity: 'error',
      });
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading settings..." />;

  return (
    <Stack spacing={3}>
      <Typography variant="h5">Settings</Typography>

      {message && (
        <Alert severity={message.severity}>{message.text}</Alert>
      )}

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Microsoft Account
        </Typography>
        {authStatus?.authenticated ? (
          <Stack spacing={2}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <AccountIcon color="success" />
              <Box>
                <Typography variant="body1">
                  {authStatus.account?.name || 'Signed In'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {authStatus.account?.username || ''}
                </Typography>
              </Box>
            </Box>
            <Button
              variant="outlined"
              color="error"
              startIcon={<LogoutIcon />}
              onClick={handleLogout}
              disabled={actionLoading}
            >
              Sign Out
            </Button>
          </Stack>
        ) : (
          <Stack spacing={2}>
            <Typography variant="body2" color="text.secondary">
              Not signed in. Sign in with your Microsoft account to collect data.
            </Typography>
            {authStatus?.error && (
              <Alert severity="warning" variant="outlined">
                {authStatus.error}
              </Alert>
            )}
            <Button
              variant="contained"
              startIcon={<LoginIcon />}
              onClick={handleLogin}
              disabled={actionLoading}
            >
              {actionLoading ? 'Signing In...' : 'Sign In with Microsoft'}
            </Button>
          </Stack>
        )}
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          About DayToDay
        </Typography>
        <List dense>
          <ListItem>
            <ListItemIcon><InfoIcon /></ListItemIcon>
            <ListItemText
              primary="Version"
              secondary="1.0.0"
            />
          </ListItem>
          <ListItem>
            <ListItemIcon><FolderIcon /></ListItemIcon>
            <ListItemText
              primary="Configuration"
              secondary="Edit config/config.json to change Azure app settings and Word doc directories."
            />
          </ListItem>
        </List>
      </Paper>
    </Stack>
  );
}
