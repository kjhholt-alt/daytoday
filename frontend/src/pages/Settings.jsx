import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Stack,
  Paper,
  Chip,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Folder as FolderIcon,
  Info as InfoIcon,
  Email as EmailIcon,
  MenuBook as OneNoteIcon,
  Cloud as CloudIcon,
  CalendarMonth as CalendarIcon,
  Warning as WarningIcon,
  Computer as ComputerIcon,
} from '@mui/icons-material';
import { getStatus } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';

export default function Settings() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await getStatus();
      setStatus(res.data);
      setError(null);
    } catch (err) {
      setError('Backend not reachable. Make sure the server is running.');
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  if (loading) return <LoadingSpinner message="Loading settings..." />;

  return (
    <Stack spacing={3}>
      <Typography variant="h5">Settings</Typography>

      {error && <Alert severity="error">{error}</Alert>}

      {/* Data Sources Status */}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Data Sources
        </Typography>
        <Stack spacing={2}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <EmailIcon color={status?.outlook_enabled ? 'success' : 'warning'} />
            <Box sx={{ flex: 1 }}>
              <Typography variant="body1">Outlook Calendar</Typography>
              <Typography variant="body2" color="text.secondary">
                {status?.outlook_enabled
                  ? 'Reading directly from Classic Outlook via COM automation'
                  : 'Outlook integration disabled'}
              </Typography>
            </Box>
            <Chip
              icon={status?.outlook_enabled ? <CheckIcon /> : <WarningIcon />}
              label={status?.outlook_enabled ? 'Active' : 'Disabled'}
              color={status?.outlook_enabled ? 'success' : 'warning'}
              size="small"
              variant="outlined"
            />
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <OneNoteIcon color={status?.onenote_enabled ? 'success' : 'warning'} />
            <Box sx={{ flex: 1 }}>
              <Typography variant="body1">OneNote Notes</Typography>
              <Typography variant="body2" color="text.secondary">
                Scanning local OneNote backup files for recent pages
              </Typography>
            </Box>
            <Chip
              icon={status?.onenote_enabled ? <CheckIcon /> : <WarningIcon />}
              label={status?.onenote_enabled ? 'Active' : 'Disabled'}
              color={status?.onenote_enabled ? 'success' : 'warning'}
              size="small"
              variant="outlined"
            />
          </Box>

          {status?.word_doc_directories && status.word_doc_directories.length > 0 && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <FolderIcon color="success" />
              <Box sx={{ flex: 1 }}>
                <Typography variant="body1">Word Documents</Typography>
                <Typography variant="body2" color="text.secondary">
                  Scanning {status.word_doc_directories.length} folder{status.word_doc_directories.length > 1 ? 's' : ''} for .docx files
                </Typography>
              </Box>
              <Chip
                icon={<CheckIcon />}
                label="Active"
                color="success"
                size="small"
                variant="outlined"
              />
            </Box>
          )}
        </Stack>
      </Paper>

      {/* Classic Outlook Requirement */}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          <CalendarIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
          Calendar Setup
        </Typography>
        <Alert severity="info" icon={<ComputerIcon />} sx={{ mb: 2 }}>
          <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
            This app requires Classic Outlook (not "New Outlook")
          </Typography>
          <Typography variant="body2" component="div">
            DayToDay reads your calendar directly from the Outlook desktop app using COM automation.
            This only works with <strong>Classic Outlook</strong>. If you've been switched to "New Outlook"
            and can't find the toggle to switch back:
          </Typography>
          <Box sx={{
            mt: 1.5, p: 1.5, borderRadius: 1,
            bgcolor: 'action.hover',
          }}>
            <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
              How to open Classic Outlook:
            </Typography>
            <Typography variant="body2" component="div">
              <ol style={{ margin: '4px 0', paddingLeft: '20px' }}>
                <li>Press <strong>Win + R</strong> to open the Run dialog</li>
                <li>Type <strong>outlook.exe</strong> and press Enter</li>
                <li>This launches Classic Outlook directly, bypassing the New Outlook toggle</li>
              </ol>
            </Typography>
          </Box>
          <Typography variant="body2" sx={{ mt: 1.5 }}>
            Make sure Outlook is running before clicking "Collect Now" in the app.
            The app will automatically read your meetings, attendees, Teams links, and more.
          </Typography>
        </Alert>

        <Alert severity="success" variant="outlined">
          <Typography variant="body2">
            <strong>No setup required!</strong> As long as Classic Outlook is running,
            DayToDay will automatically pull your calendar data when you click "Collect Now".
            No exports, no URLs, no permissions needed.
          </Typography>
        </Alert>
      </Paper>

      {/* Configured Folders */}
      {status?.word_doc_directories && status.word_doc_directories.length > 0 && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Configured Folders
          </Typography>
          <List dense>
            {status.word_doc_directories.map((dir, index) => (
              <ListItem key={index}>
                <ListItemIcon><FolderIcon /></ListItemIcon>
                <ListItemText
                  primary={dir}
                  secondary="Word documents"
                />
              </ListItem>
            ))}
          </List>
        </Paper>
      )}

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          About DayToDay
        </Typography>
        <List dense>
          <ListItem>
            <ListItemIcon><InfoIcon /></ListItemIcon>
            <ListItemText
              primary="Version"
              secondary={status?.version || '1.0.0'}
            />
          </ListItem>
          <ListItem>
            <ListItemIcon><CloudIcon /></ListItemIcon>
            <ListItemText
              primary="Data Sources"
              secondary="Outlook Calendar (COM), OneNote (local backup scanning), Word documents (local .docx scanning)"
            />
          </ListItem>
        </List>
      </Paper>
    </Stack>
  );
}
