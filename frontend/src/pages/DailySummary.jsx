import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Stack,
  Paper,
  Alert,
  Button,
} from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import dayjs from 'dayjs';
import { getToday, getByDate, triggerCollection } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import MeetingCard from '../components/MeetingCard';
import NotesList from '../components/NotesList';
import WordDocPreview from '../components/WordDocPreview';
import LoadingSpinner from '../components/LoadingSpinner';

export default function DailySummary() {
  const { date } = useParams();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [collecting, setCollecting] = useState(false);

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = date ? await getByDate(date) : await getToday();
      setSummary(res.data);
    } catch (err) {
      if (err.response?.status === 404) {
        setSummary(null);
      } else {
        setError(err.response?.data?.detail || 'Failed to load summary.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date]);

  const handleCollectAndRefresh = async () => {
    setCollecting(true);
    try {
      const targetDate = date || dayjs().format('YYYY-MM-DD');
      await triggerCollection(targetDate);
      await fetchSummary();
    } catch (err) {
      setError(err.response?.data?.detail || 'Collection failed.');
    } finally {
      setCollecting(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading daily summary..." />;

  const displayDate = date
    ? dayjs(date).format('dddd, MMMM D, YYYY')
    : dayjs().format('dddd, MMMM D, YYYY');

  if (!summary) {
    return (
      <Box sx={{ textAlign: 'center', py: 6 }}>
        <Typography variant="h5" gutterBottom>
          {displayDate}
        </Typography>
        <Typography variant="body1" color="text.secondary" gutterBottom>
          No data collected for this day yet.
        </Typography>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={handleCollectAndRefresh}
          disabled={collecting}
          sx={{ mt: 2 }}
        >
          {collecting ? 'Collecting...' : 'Collect Now'}
        </Button>
      </Box>
    );
  }

  return (
    <Stack spacing={3}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
        <Box>
          <Typography variant="h5">{displayDate}</Typography>
          <Typography variant="body2" color="text.secondary">
            Last updated: {dayjs(summary.updated_at).format('h:mm A')}
          </Typography>
        </Box>
        <StatusBadge status={summary.status} />
      </Box>

      {error && <Alert severity="error">{error}</Alert>}
      {summary.error_message && (
        <Alert severity="warning">
          Collection completed with issues: {summary.error_message}
        </Alert>
      )}

      {summary.meetings && summary.meetings.length > 0 && (
        <Box>
          <Typography variant="h6" gutterBottom>
            Meetings ({summary.meetings.length})
          </Typography>
          {summary.meetings.map((meeting) => (
            <MeetingCard key={meeting.id} meeting={meeting} />
          ))}
        </Box>
      )}

      {summary.note_references && summary.note_references.length > 0 && (
        <NotesList notes={summary.note_references} />
      )}

      {summary.word_documents && summary.word_documents.length > 0 && (
        <WordDocPreview documents={summary.word_documents} />
      )}

      {summary.summary_text && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Summary
          </Typography>
          <Typography
            variant="body2"
            component="pre"
            sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}
          >
            {summary.summary_text}
          </Typography>
        </Paper>
      )}
    </Stack>
  );
}
