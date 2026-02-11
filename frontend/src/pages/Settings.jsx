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
  TextField,
  Button,
  IconButton,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Collapse,
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
  Add as AddIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  Bolt as BoltIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';
import { getStatus, saveConfig, getCalendarImportStatus } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';

const CALENDAR_SOURCE_OPTIONS = [
  { value: 'auto', label: 'Auto (try all sources)', description: 'COM \u2192 Power Automate \u2192 Graph API' },
  { value: 'com', label: 'COM (Classic Outlook)', description: 'Read directly from Classic Outlook desktop app' },
  { value: 'power_automate', label: 'Power Automate', description: 'Read from JSON files exported by a Power Automate flow' },
  { value: 'graph', label: 'Graph API', description: 'Use Microsoft Graph API (requires auth)' },
];

export default function Settings() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notebooks, setNotebooks] = useState([]);
  const [newNotebook, setNewNotebook] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState(null);

  // Calendar source state
  const [calendarSource, setCalendarSource] = useState('auto');
  const [paExportPath, setPaExportPath] = useState('');
  const [calSaving, setCalSaving] = useState(false);
  const [calSaveMessage, setCalSaveMessage] = useState(null);
  const [paTestResult, setPaTestResult] = useState(null);
  const [paTesting, setPaTesting] = useState(false);
  const [showPaGuide, setShowPaGuide] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await getStatus();
      setStatus(res.data);
      setNotebooks(res.data.onenote_notebooks || []);
      setCalendarSource(res.data.calendar_source || 'auto');
      setPaExportPath(res.data.power_automate_export_path || '');
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

  const handleAddNotebook = () => {
    const trimmed = newNotebook.trim();
    if (trimmed && !notebooks.includes(trimmed)) {
      setNotebooks([...notebooks, trimmed]);
      setNewNotebook('');
    }
  };

  const handleRemoveNotebook = (index) => {
    setNotebooks(notebooks.filter((_, i) => i !== index));
  };

  const handleSaveNotebooks = async () => {
    setSaving(true);
    setSaveMessage(null);
    try {
      await saveConfig({ onenote_notebooks: notebooks });
      setSaveMessage({ type: 'success', text: 'Notebook filter saved! Re-run collection to apply.' });
    } catch (err) {
      setSaveMessage({ type: 'error', text: 'Failed to save notebook filter.' });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveCalendarSource = async () => {
    setCalSaving(true);
    setCalSaveMessage(null);
    try {
      await saveConfig({
        calendar_source: calendarSource,
        power_automate_export_path: paExportPath,
      });
      setCalSaveMessage({ type: 'success', text: 'Calendar source saved! Re-run collection to apply.' });
      fetchStatus();
    } catch (err) {
      setCalSaveMessage({ type: 'error', text: 'Failed to save calendar source.' });
    } finally {
      setCalSaving(false);
    }
  };

  const handleTestPa = async () => {
    setPaTesting(true);
    setPaTestResult(null);
    try {
      const res = await getCalendarImportStatus();
      setPaTestResult(res.data);
    } catch (err) {
      setPaTestResult({ error: 'Failed to check Power Automate status.' });
    } finally {
      setPaTesting(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading settings..." />;

  const paStatus = status?.power_automate_status || {};
  const calSourceLabel = CALENDAR_SOURCE_OPTIONS.find(o => o.value === (status?.calendar_source || 'auto'))?.label || 'Auto';

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
            <CalendarIcon color={status?.outlook_enabled ? 'success' : 'warning'} />
            <Box sx={{ flex: 1 }}>
              <Typography variant="body1">Calendar</Typography>
              <Typography variant="body2" color="text.secondary">
                Source: {calSourceLabel}
                {paStatus?.file_found && calendarSource !== 'com' && calendarSource !== 'graph' && (
                  <> &mdash; PA file found with {paStatus.event_count} event(s)</>
                )}
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

      {/* Calendar Source Setup */}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          <CalendarIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
          Calendar Setup
        </Typography>

        {calSaveMessage && (
          <Alert severity={calSaveMessage.type} sx={{ mb: 2 }} onClose={() => setCalSaveMessage(null)}>
            {calSaveMessage.text}
          </Alert>
        )}

        <FormControl fullWidth size="small" sx={{ mb: 2 }}>
          <InputLabel>Calendar Source</InputLabel>
          <Select
            value={calendarSource}
            label="Calendar Source"
            onChange={(e) => setCalendarSource(e.target.value)}
          >
            {CALENDAR_SOURCE_OPTIONS.map((opt) => (
              <MenuItem key={opt.value} value={opt.value}>
                <Box>
                  <Typography variant="body2">{opt.label}</Typography>
                  <Typography variant="caption" color="text.secondary">{opt.description}</Typography>
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* COM info */}
        {(calendarSource === 'auto' || calendarSource === 'com') && (
          <Alert severity="info" icon={<ComputerIcon />} sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
              COM (Classic Outlook)
            </Typography>
            <Typography variant="body2">
              Reads directly from Outlook desktop app. Requires <strong>Classic Outlook</strong> to be running.
              Press <strong>Win + R</strong>, type <strong>outlook.exe</strong> to launch it.
            </Typography>
          </Alert>
        )}

        {/* Power Automate config */}
        {(calendarSource === 'auto' || calendarSource === 'power_automate') && (
          <Box sx={{ mb: 2 }}>
            <Alert severity="info" icon={<BoltIcon />} sx={{ mb: 2 }}>
              <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                Power Automate
              </Typography>
              <Typography variant="body2">
                Uses a Power Automate flow to export calendar data as JSON. Works with New Outlook
                and bypasses Graph API auth restrictions.
              </Typography>
            </Alert>

            <TextField
              fullWidth
              size="small"
              label="Export folder path"
              placeholder="Leave empty to auto-detect OneDrive/DayToDay"
              value={paExportPath}
              onChange={(e) => setPaExportPath(e.target.value)}
              helperText={paStatus?.export_path ? `Auto-detected: ${paStatus.export_path}` : 'Set the folder where Power Automate writes calendar JSON files'}
              sx={{ mb: 1 }}
            />

            <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
              <Button
                variant="outlined"
                size="small"
                onClick={handleTestPa}
                disabled={paTesting}
              >
                {paTesting ? 'Testing...' : 'Test Connection'}
              </Button>
            </Box>

            {paTestResult && !paTestResult.error && (
              <Alert severity={paTestResult.file_found ? 'success' : 'warning'} sx={{ mb: 1 }}>
                {paTestResult.file_found ? (
                  <Typography variant="body2">
                    Found export file with <strong>{paTestResult.event_count}</strong> event(s).
                    Last modified: {new Date(paTestResult.file_modified).toLocaleString()}
                  </Typography>
                ) : (
                  <Typography variant="body2">
                    Export folder exists ({paTestResult.export_path}) but no calendar file found yet.
                    Run your Power Automate flow to create one.
                  </Typography>
                )}
              </Alert>
            )}
            {paTestResult?.error && (
              <Alert severity="error" sx={{ mb: 1 }}>{paTestResult.error}</Alert>
            )}

            {/* Setup guide toggle */}
            <Button
              size="small"
              onClick={() => setShowPaGuide(!showPaGuide)}
              endIcon={showPaGuide ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              sx={{ mb: 1, textTransform: 'none' }}
            >
              {showPaGuide ? 'Hide setup guide' : 'How to set up the Power Automate flow'}
            </Button>

            <Collapse in={showPaGuide}>
              <Box sx={{ p: 2, borderRadius: 1, bgcolor: 'action.hover' }}>
                <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                  Power Automate Flow Setup
                </Typography>
                <Typography variant="body2" component="div">
                  <ol style={{ margin: '4px 0', paddingLeft: '20px', lineHeight: 1.8 }}>
                    <li>
                      Go to <strong>make.powerautomate.com</strong> and sign in with your work account
                    </li>
                    <li>
                      Click <strong>Create</strong> &rarr; <strong>Instant cloud flow</strong> (or Scheduled for automatic runs)
                    </li>
                    <li>
                      Add trigger: <strong>Manually trigger a flow</strong> (or <strong>Recurrence</strong> for daily)
                    </li>
                    <li>
                      Add action: <strong>Office 365 Outlook &ndash; Get calendar view of events (V3)</strong>
                      <ul style={{ paddingLeft: '16px', margin: '4px 0' }}>
                        <li>Calendar ID: <em>Calendar</em></li>
                        <li>Start Time: <code>startOfDay(utcNow())</code></li>
                        <li>End Time: <code>addDays(startOfDay(utcNow()), 1)</code></li>
                      </ul>
                    </li>
                    <li>
                      Add action: <strong>OneDrive for Business &ndash; Create file</strong>
                      <ul style={{ paddingLeft: '16px', margin: '4px 0' }}>
                        <li>Folder Path: <code>/DayToDay</code></li>
                        <li>File Name: <code>calendar_events.json</code></li>
                        <li>File Content: select the <strong>value</strong> output from the calendar action</li>
                      </ul>
                    </li>
                    <li>
                      Save and run the flow. The file will appear in your OneDrive/DayToDay folder.
                    </li>
                  </ol>
                </Typography>
                <Alert severity="info" variant="outlined" sx={{ mt: 1 }}>
                  <Typography variant="body2">
                    <strong>Alternative:</strong> Instead of OneDrive, the flow can POST directly to this app:
                    add an <strong>HTTP</strong> action that POSTs to{' '}
                    <code>http://localhost:8000/api/calendar/import/</code> with the body:{' '}
                    <code>{`{"events": <value output>, "date": "<today>"}`}</code>
                  </Typography>
                </Alert>
              </Box>
            </Collapse>
          </Box>
        )}

        <Button
          variant="contained"
          size="small"
          startIcon={<SaveIcon />}
          onClick={handleSaveCalendarSource}
          disabled={calSaving}
        >
          {calSaving ? 'Saving...' : 'Save Calendar Settings'}
        </Button>
      </Paper>

      {/* OneNote Notebook Filter */}
      {status?.onenote_enabled && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            <OneNoteIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
            OneNote Notebook Filter
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Only include pages from these notebooks. Leave empty to include all notebooks.
          </Typography>

          {saveMessage && (
            <Alert severity={saveMessage.type} sx={{ mb: 2 }} onClose={() => setSaveMessage(null)}>
              {saveMessage.text}
            </Alert>
          )}

          {notebooks.length > 0 && (
            <List dense sx={{ mb: 1 }}>
              {notebooks.map((nb, index) => (
                <ListItem
                  key={index}
                  secondaryAction={
                    <IconButton edge="end" size="small" onClick={() => handleRemoveNotebook(index)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  }
                >
                  <ListItemIcon><OneNoteIcon fontSize="small" /></ListItemIcon>
                  <ListItemText primary={nb} />
                </ListItem>
              ))}
            </List>
          )}

          {notebooks.length === 0 && (
            <Alert severity="info" variant="outlined" sx={{ mb: 2 }}>
              No filter set — all notebooks will be included.
            </Alert>
          )}

          <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
            <TextField
              size="small"
              placeholder="Notebook name (e.g. Notes FY25)"
              value={newNotebook}
              onChange={(e) => setNewNotebook(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddNotebook()}
              sx={{ flex: 1 }}
            />
            <Button
              variant="outlined"
              size="small"
              startIcon={<AddIcon />}
              onClick={handleAddNotebook}
              disabled={!newNotebook.trim()}
            >
              Add
            </Button>
          </Box>
          <Button
            variant="contained"
            size="small"
            startIcon={<SaveIcon />}
            onClick={handleSaveNotebooks}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Filter'}
          </Button>
        </Paper>
      )}

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
              secondary="Outlook Calendar (COM / Power Automate / Graph API), OneNote (local backup scanning), Word documents (local .docx scanning)"
            />
          </ListItem>
        </List>
      </Paper>
    </Stack>
  );
}
