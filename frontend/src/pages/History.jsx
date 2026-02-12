import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActionArea,
  Stack,
  Pagination,
  Chip,
} from '@mui/material';
import {
  Event as EventIcon,
  Note as NoteIcon,
  Description as DocIcon,
} from '@mui/icons-material';
import dayjs from 'dayjs';
import { getHistory } from '../services/api';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import CalendarHeatmap from '../components/CalendarHeatmap';

export default function History() {
  const navigate = useNavigate();
  const [summaries, setSummaries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const res = await getHistory(page);
        setSummaries(res.data.results || []);
        const count = res.data.count || 0;
        setTotalPages(Math.ceil(count / 20));
      } catch (err) {
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [page]);

  if (loading) return <LoadingSpinner message="Loading history..." />;

  if (summaries.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 6 }}>
        <Typography variant="h5" gutterBottom>History</Typography>
        <Typography color="text.secondary">
          No daily summaries collected yet. Use "Run Collection" to get started.
        </Typography>
      </Box>
    );
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h5">History</Typography>
      <CalendarHeatmap />
      {summaries.map((s) => (
        <Card key={s.id} variant="outlined">
          <CardActionArea onClick={() => navigate(`/day/${s.date}`)}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="h6">
                  {dayjs(s.date).format('dddd, MMMM D, YYYY')}
                </Typography>
                <StatusBadge status={s.status} />
              </Box>
              <Stack direction="row" spacing={2}>
                <Chip icon={<EventIcon />} label={`${s.meeting_count || 0} meetings`} size="small" variant="outlined" />
                <Chip icon={<NoteIcon />} label={`${s.note_count || 0} notes`} size="small" variant="outlined" />
                <Chip icon={<DocIcon />} label={`${s.doc_count || 0} docs`} size="small" variant="outlined" />
              </Stack>
            </CardContent>
          </CardActionArea>
        </Card>
      ))}
      {totalPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={(_, v) => setPage(v)}
            color="primary"
          />
        </Box>
      )}
    </Stack>
  );
}
