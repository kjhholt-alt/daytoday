import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Typography,
  TextField,
  InputAdornment,
  Stack,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Paper,
  Box,
  Collapse,
  IconButton,
  Tooltip,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  Search as SearchIcon,
  Event as EventIcon,
  Note as NoteIcon,
  Description as DocIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';
import dayjs from 'dayjs';
import { search, openNote } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';

function NoteSearchItem({ note, searchQuery }) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'success' });
  const hasContent = note.content_snippet && note.content_snippet.trim().length > 0;

  const handleOpenNote = async (e) => {
    e.stopPropagation();
    try {
      const res = await openNote(note.id);
      if (res.data.action === 'open_url') {
        window.open(res.data.url, '_blank');
      } else {
        setSnack({ open: true, message: res.data.detail || 'Opened in OneNote', severity: 'success' });
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Could not open note';
      setSnack({ open: true, message: msg, severity: 'error' });
    }
  };

  const handleClick = () => {
    setExpanded(!expanded);
  };

  const noteDate = note.daily_summary?.date;

  const renderContentLines = () => {
    if (!note.content_snippet) return null;
    const lines = note.content_snippet.split('\n').filter((l) => l.trim());
    return lines.map((line, i) => (
      <Typography
        key={i}
        variant="body2"
        onClick={(e) => { e.stopPropagation(); handleOpenNote(e); }}
        sx={{
          cursor: 'pointer',
          py: 0.3,
          px: 0.5,
          borderRadius: 0.5,
          fontSize: '0.85rem',
          lineHeight: 1.6,
          '&:hover': {
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
          },
        }}
      >
        {line}
      </Typography>
    ));
  };

  return (
    <>
      <ListItem
        button
        onClick={handleClick}
        sx={{
          flexDirection: 'column',
          alignItems: 'flex-start',
          '&:hover': { bgcolor: 'action.hover' },
        }}
      >
        <Box sx={{ display: 'flex', width: '100%', alignItems: 'flex-start' }}>
          <ListItemIcon><NoteIcon color="primary" /></ListItemIcon>
          <ListItemText
            primary={
              <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.5 }}>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  {note.page_title}
                </Typography>
                <Tooltip title="Open in OneNote">
                  <IconButton size="small" onClick={handleOpenNote} color="primary">
                    <OpenInNewIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                {hasContent && (
                  <IconButton size="small">
                    {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                  </IconButton>
                )}
              </Box>
            }
            secondary={
              <Box component="span">
                {[note.notebook_name, note.section_name].filter(Boolean).join(' > ')}
                {noteDate && (
                  <Typography
                    variant="caption"
                    component="span"
                    color="primary"
                    sx={{ ml: 1, cursor: 'pointer', textDecoration: 'underline' }}
                    onClick={(e) => { e.stopPropagation(); navigate(`/day/${noteDate}`); }}
                  >
                    View day
                  </Typography>
                )}
              </Box>
            }
          />
        </Box>
        {hasContent && (
          <Collapse in={expanded} sx={{ width: '100%', pl: 7 }}>
            <Box
              sx={{
                mt: 0.5,
                mb: 1,
                p: 1.5,
                bgcolor: 'action.hover',
                borderRadius: 1,
                borderLeft: 3,
                borderColor: 'primary.main',
                maxHeight: 300,
                overflow: 'auto',
              }}
            >
              {renderContentLines()}
            </Box>
          </Collapse>
        )}
      </ListItem>
      <Snackbar
        open={snack.open}
        autoHideDuration={3000}
        onClose={() => setSnack({ ...snack, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snack.severity} onClose={() => setSnack({ ...snack, open: false })}>
          {snack.message}
        </Alert>
      </Snackbar>
    </>
  );
}

export default function Search() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState(0);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await search(query.trim());
      setResults(res.data);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const totalResults = results
    ? (results.meetings?.length || 0) +
      (results.notes?.length || 0) +
      (results.documents?.length || 0)
    : 0;

  return (
    <Stack spacing={3}>
      <Typography variant="h5">Search</Typography>
      <form onSubmit={handleSearch}>
        <TextField
          fullWidth
          placeholder="Search meetings, notes, documents..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
      </form>

      {loading && <LoadingSpinner message="Searching..." />}

      {results && !loading && (
        <>
          <Typography variant="body2" color="text.secondary">
            {totalResults} result(s) found
          </Typography>
          <Tabs value={tab} onChange={(_, v) => setTab(v)}>
            <Tab label={`Meetings (${results.meetings?.length || 0})`} />
            <Tab label={`Notes (${results.notes?.length || 0})`} />
            <Tab label={`Documents (${results.documents?.length || 0})`} />
          </Tabs>

          {tab === 0 && (
            <Paper variant="outlined">
              <List>
                {(results.meetings || []).map((m) => (
                  <ListItem key={m.id} button onClick={() => {
                    const d = dayjs(m.start_time).format('YYYY-MM-DD');
                    navigate(`/day/${d}`);
                  }}>
                    <ListItemIcon><EventIcon /></ListItemIcon>
                    <ListItemText
                      primary={m.subject}
                      secondary={`${dayjs(m.start_time).format('MMM D, YYYY h:mm A')} - ${m.organizer_name}`}
                    />
                  </ListItem>
                ))}
                {(!results.meetings || results.meetings.length === 0) && (
                  <ListItem>
                    <ListItemText primary="No matching meetings." primaryTypographyProps={{ color: 'text.secondary' }} />
                  </ListItem>
                )}
              </List>
            </Paper>
          )}

          {tab === 1 && (
            <Paper variant="outlined">
              <List>
                {(results.notes || []).map((n) => (
                  <NoteSearchItem key={n.id} note={n} searchQuery={query} />
                ))}
                {(!results.notes || results.notes.length === 0) && (
                  <ListItem>
                    <ListItemText primary="No matching notes." primaryTypographyProps={{ color: 'text.secondary' }} />
                  </ListItem>
                )}
              </List>
            </Paper>
          )}

          {tab === 2 && (
            <Paper variant="outlined">
              <List>
                {(results.documents || []).map((d) => (
                  <ListItem key={d.id}>
                    <ListItemIcon><DocIcon /></ListItemIcon>
                    <ListItemText
                      primary={d.file_name}
                      secondary={d.file_path}
                    />
                  </ListItem>
                ))}
                {(!results.documents || results.documents.length === 0) && (
                  <ListItem>
                    <ListItemText primary="No matching documents." primaryTypographyProps={{ color: 'text.secondary' }} />
                  </ListItem>
                )}
              </List>
            </Paper>
          )}
        </>
      )}
    </Stack>
  );
}
