import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Stack,
  Paper,
  Alert,
  Button,
  Snackbar,
  LinearProgress,
} from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import dayjs from 'dayjs';
import { getToday, getByDate, triggerCollection } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import MeetingCard from '../components/MeetingCard';
import NotesList from '../components/NotesList';
import WordDocPreview from '../components/WordDocPreview';
import LoadingSpinner from '../components/LoadingSpinner';
import NextUpBanner from '../components/NextUpBanner';
import QuickStatsBar from '../components/QuickStatsBar';

// Simple markdown-to-HTML converter for our structured summary text
function simpleMarkdown(text) {
  if (!text) return '';
  return text
    .split('\n')
    .map(line => {
      if (line.startsWith('### ')) return `<h3>${line.slice(4)}</h3>`;
      if (line.startsWith('## ')) return `<h2>${line.slice(3)}</h2>`;
      if (line.startsWith('# ')) return `<h1>${line.slice(2)}</h1>`;
      if (line.startsWith('  - ')) return `<li style="margin-left:20px">${line.slice(4)}</li>`;
      if (line.startsWith('- ')) return `<li>${line.slice(2)}</li>`;
      if (line.trim() === '') return '';
      return `<p>${line}</p>`;
    })
    .join('\n')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>');
}

const COLLECTION_STEPS = [
  'Collecting calendar events...',
  'Scanning OneNote pages...',
  'Scanning documents...',
  'Finalizing summary...',
];

export default function DailySummary() {
  const { date } = useParams();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [collecting, setCollecting] = useState(false);
  const [collectionStep, setCollectionStep] = useState(0);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

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

  // Animate collection step text while collecting
  useEffect(() => {
    if (!collecting) {
      setCollectionStep(0);
      return;
    }
    let step = 0;
    setCollectionStep(0);
    const interval = setInterval(() => {
      step += 1;
      if (step < COLLECTION_STEPS.length) {
        setCollectionStep(step);
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [collecting]);

  const handleCollectAndRefresh = async () => {
    setCollecting(true);
    setError(null);
    try {
      const targetDate = date || dayjs().format('YYYY-MM-DD');
      const res = await triggerCollection(targetDate);
      await fetchSummary();

      // Build a success message with counts from the collection response
      const data = res.data;
      const meetingCount = data.meetings?.length || 0;
      const noteCount = data.note_references?.length || 0;
      const docCount = data.word_documents?.length || 0;
      const recordingCount = data.recordings?.length || 0;

      const parts = [];
      if (meetingCount > 0) parts.push(`${meetingCount} meeting${meetingCount !== 1 ? 's' : ''}`);
      if (noteCount > 0) parts.push(`${noteCount} note${noteCount !== 1 ? 's' : ''}`);
      if (docCount > 0) parts.push(`${docCount} document${docCount !== 1 ? 's' : ''}`);
      if (recordingCount > 0) parts.push(`${recordingCount} recording${recordingCount !== 1 ? 's' : ''}`);

      const countMessage = parts.length > 0
        ? `Found ${parts.join(', ')}`
        : 'Collection complete (no items found)';

      setSnackbar({ open: true, message: countMessage, severity: 'success' });
    } catch (err) {
      const detail = err.response?.data?.detail || 'Collection failed.';
      setError(detail);
      setSnackbar({ open: true, message: detail, severity: 'error' });
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
        {collecting && (
          <Box sx={{ maxWidth: 400, mx: 'auto', mt: 2, mb: 1 }}>
            <LinearProgress sx={{ borderRadius: 1, mb: 1 }} />
            <Typography variant="body2" color="text.secondary">
              {COLLECTION_STEPS[collectionStep]}
            </Typography>
          </Box>
        )}
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={handleCollectAndRefresh}
          disabled={collecting}
          sx={{ mt: 2 }}
        >
          {collecting ? 'Collecting...' : 'Collect Now'}
        </Button>
        <Snackbar
          open={snackbar.open}
          autoHideDuration={5000}
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          <Alert
            severity={snackbar.severity}
            onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
            variant="filled"
          >
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Box>
    );
  }

  return (
    <Stack spacing={3}>
      {/* Header row: date, status, collect button */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
        <Box>
          <Typography variant="h5">{displayDate}</Typography>
          <Typography variant="body2" color="text.secondary">
            Last updated: {dayjs(summary.updated_at).format('h:mm A')}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <StatusBadge status={summary.status} />
          <Button
            size="small"
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleCollectAndRefresh}
            disabled={collecting}
          >
            {collecting ? 'Collecting...' : 'Collect Now'}
          </Button>
        </Stack>
      </Box>

      {/* Collection progress indicator */}
      {collecting && (
        <Box>
          <LinearProgress sx={{ borderRadius: 1, mb: 0.5 }} />
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center' }}>
            {COLLECTION_STEPS[collectionStep]}
          </Typography>
        </Box>
      )}

      {/* Quick stats bar */}
      <QuickStatsBar
        meetings={summary.meetings}
        notes={summary.note_references}
        documents={summary.word_documents}
      />

      {error && <Alert severity="error">{error}</Alert>}
      {summary.error_message && (
        <Alert severity="warning">
          Collection completed with issues: {summary.error_message}
        </Alert>
      )}

      {/* Next Up banner - only relevant for today's view */}
      {!date && summary.meetings && summary.meetings.length > 0 && (
        <NextUpBanner meetings={summary.meetings} />
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
          <Box
            sx={{
              '& h1': {
                fontSize: '1.5rem',
                fontWeight: 700,
                mt: 2,
                mb: 1,
                lineHeight: 1.3,
                color: 'text.primary',
              },
              '& h2': {
                fontSize: '1.25rem',
                fontWeight: 600,
                mt: 2.5,
                mb: 1,
                lineHeight: 1.3,
                color: 'text.primary',
              },
              '& h3': {
                fontSize: '1.1rem',
                fontWeight: 600,
                mt: 2,
                mb: 0.5,
                lineHeight: 1.4,
                color: 'text.primary',
              },
              '& h4': {
                fontSize: '1rem',
                fontWeight: 600,
                mt: 1.5,
                mb: 0.5,
                color: 'text.primary',
              },
              '& p': {
                fontSize: '0.875rem',
                lineHeight: 1.6,
                mb: 1,
                color: 'text.secondary',
              },
              '& ul, & ol': {
                pl: 2.5,
                mb: 1,
              },
              '& li': {
                fontSize: '0.875rem',
                lineHeight: 1.6,
                color: 'text.secondary',
                mb: 0.25,
              },
              '& strong': {
                fontWeight: 600,
                color: 'text.primary',
              },
              '& em': {
                fontStyle: 'italic',
              },
              '& hr': {
                border: 'none',
                borderTop: '1px solid',
                borderColor: 'divider',
                my: 2,
              },
              '& code': {
                fontFamily: 'monospace',
                fontSize: '0.8rem',
                bgcolor: 'grey.100',
                px: 0.5,
                py: 0.25,
                borderRadius: 0.5,
              },
              '& pre': {
                bgcolor: 'grey.100',
                p: 1.5,
                borderRadius: 1,
                overflow: 'auto',
                mb: 1,
              },
              '& pre code': {
                bgcolor: 'transparent',
                px: 0,
                py: 0,
              },
              '& a': {
                color: 'primary.main',
                textDecoration: 'underline',
              },
              '& blockquote': {
                borderLeft: '3px solid',
                borderColor: 'primary.main',
                pl: 2,
                ml: 0,
                my: 1,
                color: 'text.secondary',
                fontStyle: 'italic',
              },
              '& > *:first-of-type': {
                mt: 0,
              },
            }}
          >
            <div dangerouslySetInnerHTML={{ __html: simpleMarkdown(summary.summary_text) }} />
          </Box>
        </Paper>
      )}

      {/* Snackbar for collection feedback */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={5000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity={snackbar.severity}
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Stack>
  );
}
