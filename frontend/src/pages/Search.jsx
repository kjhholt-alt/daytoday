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
} from '@mui/material';
import {
  Search as SearchIcon,
  Event as EventIcon,
  Note as NoteIcon,
  Description as DocIcon,
} from '@mui/icons-material';
import dayjs from 'dayjs';
import { search } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';

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
                  <ListItem key={n.id}>
                    <ListItemIcon><NoteIcon /></ListItemIcon>
                    <ListItemText
                      primary={n.page_title}
                      secondary={n.section_name || null}
                    />
                  </ListItem>
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
