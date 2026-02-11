import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Stack,
  Paper,
  TextField,
  InputAdornment,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
  Chip,
  CircularProgress,
  Alert,
  Divider,
} from '@mui/material';
import {
  Search as SearchIcon,
  CalendarMonth as CalendarIcon,
  AccessTime as TimeIcon,
  Group as GroupIcon,
} from '@mui/icons-material';
import { useSearchParams } from 'react-router-dom';
import dayjs from 'dayjs';
import { searchAttendees, getTopAttendees } from '../services/api';

function stringToColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash % 360);
  return `hsl(${hue}, 55%, 50%)`;
}

function getInitials(name) {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0][0].toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default function People() {
  const [searchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || '';

  const [query, setQuery] = useState(initialQuery);
  const [topAttendees, setTopAttendees] = useState([]);
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  const [loadingTop, setLoadingTop] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPerson, setSelectedPerson] = useState(null);
  const [personMeetings, setPersonMeetings] = useState([]);
  const [loadingMeetings, setLoadingMeetings] = useState(false);

  // Load top collaborators on mount
  useEffect(() => {
    loadTopAttendees();
  }, []);

  // Auto-search if navigated with ?q= parameter
  useEffect(() => {
    if (initialQuery) {
      handleSelectPerson(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);

  const loadTopAttendees = async () => {
    try {
      const res = await getTopAttendees(25);
      setTopAttendees(res.data.attendees || []);
    } catch (err) {
      setError('Failed to load collaborator data.');
    } finally {
      setLoadingTop(false);
    }
  };

  const handleSearch = async (searchQuery) => {
    setQuery(searchQuery);
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }

    setSearching(true);
    try {
      const res = await searchAttendees(searchQuery.trim());
      setSearchResults(res.data);
    } catch (err) {
      setError('Search failed.');
    } finally {
      setSearching(false);
    }
  };

  const handleSelectPerson = async (name) => {
    setSelectedPerson(name);
    setLoadingMeetings(true);
    try {
      const res = await searchAttendees(name);
      setPersonMeetings(res.data.meetings || []);
    } catch (err) {
      setPersonMeetings([]);
    } finally {
      setLoadingMeetings(false);
    }
  };

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (query.trim().length >= 2) {
        handleSearch(query);
      } else {
        setSearchResults(null);
      }
    }, 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  return (
    <Stack spacing={3}>
      <Typography variant="h5">
        <GroupIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
        People
      </Typography>

      {error && <Alert severity="error" onClose={() => setError(null)}>{error}</Alert>}

      {/* Search */}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <TextField
          fullWidth
          placeholder="Search by name or email..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
            endAdornment: searching ? (
              <InputAdornment position="end">
                <CircularProgress size={20} />
              </InputAdornment>
            ) : null,
          }}
          size="small"
        />
      </Paper>

      {/* Person detail view */}
      {selectedPerson && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Avatar sx={{ bgcolor: stringToColor(selectedPerson), width: 48, height: 48 }}>
              {getInitials(selectedPerson)}
            </Avatar>
            <Box sx={{ flex: 1 }}>
              <Typography variant="h6">{selectedPerson}</Typography>
              <Typography variant="body2" color="text.secondary">
                {personMeetings.length} meeting{personMeetings.length !== 1 ? 's' : ''} together
              </Typography>
            </Box>
            <Chip
              label="Close"
              size="small"
              onClick={() => { setSelectedPerson(null); setPersonMeetings([]); }}
            />
          </Box>

          {loadingMeetings ? (
            <Box sx={{ textAlign: 'center', py: 2 }}>
              <CircularProgress size={24} />
            </Box>
          ) : personMeetings.length === 0 ? (
            <Typography variant="body2" color="text.secondary">No meetings found.</Typography>
          ) : (
            <List dense>
              {personMeetings.map((meeting, idx) => (
                <React.Fragment key={meeting.id}>
                  <ListItem alignItems="flex-start">
                    <ListItemAvatar>
                      <Avatar sx={{ bgcolor: 'primary.main', width: 36, height: 36 }}>
                        <CalendarIcon sx={{ fontSize: 20 }} />
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={meeting.subject}
                      secondary={
                        <Box component="span" sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 0.5 }}>
                          <Chip
                            icon={<CalendarIcon sx={{ fontSize: 14 }} />}
                            label={dayjs(meeting.date).format('MMM D, YYYY')}
                            size="small"
                            variant="outlined"
                            sx={{ height: 22, fontSize: '0.7rem' }}
                          />
                          <Chip
                            icon={<TimeIcon sx={{ fontSize: 14 }} />}
                            label={`${dayjs(meeting.start_time).format('h:mm A')} - ${dayjs(meeting.end_time).format('h:mm A')}`}
                            size="small"
                            variant="outlined"
                            sx={{ height: 22, fontSize: '0.7rem' }}
                          />
                          {meeting.attendee_count > 0 && (
                            <Chip
                              icon={<GroupIcon sx={{ fontSize: 14 }} />}
                              label={meeting.attendee_count}
                              size="small"
                              variant="outlined"
                              sx={{ height: 22, fontSize: '0.7rem' }}
                            />
                          )}
                        </Box>
                      }
                      primaryTypographyProps={{ variant: 'body2', fontWeight: 'medium' }}
                    />
                  </ListItem>
                  {idx < personMeetings.length - 1 && <Divider variant="inset" component="li" />}
                </React.Fragment>
              ))}
            </List>
          )}
        </Paper>
      )}

      {/* Search results */}
      {searchResults && !selectedPerson && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Search Results ({searchResults.count} meetings)
          </Typography>
          {searchResults.meetings.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No meetings found with "{searchResults.query}"
            </Typography>
          ) : (
            <List dense>
              {searchResults.meetings.map((meeting, idx) => (
                <React.Fragment key={meeting.id}>
                  <ListItem>
                    <ListItemText
                      primary={meeting.subject}
                      secondary={`${dayjs(meeting.date).format('MMM D, YYYY')} | ${dayjs(meeting.start_time).format('h:mm A')} - ${dayjs(meeting.end_time).format('h:mm A')} | ${meeting.organizer_name}`}
                      primaryTypographyProps={{ variant: 'body2', fontWeight: 'medium' }}
                      secondaryTypographyProps={{ variant: 'caption' }}
                    />
                  </ListItem>
                  {idx < searchResults.meetings.length - 1 && <Divider component="li" />}
                </React.Fragment>
              ))}
            </List>
          )}
        </Paper>
      )}

      {/* Top collaborators */}
      {!selectedPerson && !searchResults && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Top Collaborators
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            People you meet with most frequently. Click a name to see all meetings.
          </Typography>

          {loadingTop ? (
            <Box sx={{ textAlign: 'center', py: 3 }}>
              <CircularProgress size={32} />
            </Box>
          ) : topAttendees.length === 0 ? (
            <Alert severity="info">
              No meeting data yet. Run a collection first to see your collaborators.
            </Alert>
          ) : (
            <List>
              {topAttendees.map((person, idx) => (
                <React.Fragment key={idx}>
                  <ListItem
                    component="div"
                    onClick={() => handleSelectPerson(person.name || person.email)}
                    sx={{
                      cursor: 'pointer',
                      borderRadius: 1,
                      '&:hover': { bgcolor: 'action.hover' },
                    }}
                  >
                    <ListItemAvatar>
                      <Avatar sx={{ bgcolor: stringToColor(person.name || person.email) }}>
                        {getInitials(person.name || person.email)}
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={person.name || person.email}
                      secondary={person.email && person.name ? person.email : null}
                      primaryTypographyProps={{ fontWeight: 'medium' }}
                    />
                    <Chip
                      label={`${person.meeting_count} meeting${person.meeting_count !== 1 ? 's' : ''}`}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  </ListItem>
                  {idx < topAttendees.length - 1 && <Divider variant="inset" component="li" />}
                </React.Fragment>
              ))}
            </List>
          )}
        </Paper>
      )}
    </Stack>
  );
}
