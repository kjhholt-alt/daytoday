import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Tooltip,
  IconButton,
  Stack,
  Chip,
} from '@mui/material';
import {
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
} from '@mui/icons-material';
import dayjs from 'dayjs';
import { getHeatmap } from '../services/api';

const INTENSITY_COLORS_LIGHT = [
  'rgba(0,0,0,0.04)',   // 0: no data
  'rgba(21,101,192,0.15)', // 1-2 items
  'rgba(21,101,192,0.35)', // 3-5 items
  'rgba(21,101,192,0.55)', // 6-9 items
  'rgba(21,101,192,0.80)', // 10+ items
];

const INTENSITY_COLORS_DARK = [
  'rgba(255,255,255,0.04)',
  'rgba(66,165,245,0.20)',
  'rgba(66,165,245,0.40)',
  'rgba(66,165,245,0.60)',
  'rgba(66,165,245,0.85)',
];

function getIntensity(total) {
  if (total === 0) return 0;
  if (total <= 2) return 1;
  if (total <= 5) return 2;
  if (total <= 9) return 3;
  return 4;
}

export default function CalendarHeatmap() {
  const navigate = useNavigate();
  const [heatmapData, setHeatmapData] = useState(null);
  const [monthOffset, setMonthOffset] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await getHeatmap(6);
        setHeatmapData(res.data);
      } catch (err) {
        console.error('Failed to load heatmap:', err);
      }
    };
    fetchData();
  }, []);

  const dayMap = useMemo(() => {
    if (!heatmapData) return {};
    const map = {};
    (heatmapData.days || []).forEach((d) => {
      map[d.date] = d;
    });
    return map;
  }, [heatmapData]);

  const currentMonth = useMemo(() => {
    return dayjs().subtract(monthOffset, 'month');
  }, [monthOffset]);

  const calendarDays = useMemo(() => {
    const startOfMonth = currentMonth.startOf('month');
    const endOfMonth = currentMonth.endOf('month');
    const startDay = startOfMonth.day(); // 0=Sunday

    const days = [];
    // Pad the beginning
    for (let i = 0; i < startDay; i++) {
      days.push(null);
    }
    // Fill in days
    for (let d = 1; d <= endOfMonth.date(); d++) {
      days.push(currentMonth.date(d).format('YYYY-MM-DD'));
    }
    return days;
  }, [currentMonth]);

  const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark'
    || window.matchMedia?.('(prefers-color-scheme: dark)').matches;

  const colors = isDarkMode ? INTENSITY_COLORS_DARK : INTENSITY_COLORS_LIGHT;
  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      {/* Month navigation */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6" sx={{ fontSize: '1rem' }}>
          Activity Calendar
        </Typography>
        <Stack direction="row" spacing={0.5} alignItems="center">
          <IconButton size="small" onClick={() => setMonthOffset((o) => o + 1)}>
            <ChevronLeftIcon fontSize="small" />
          </IconButton>
          <Chip
            label={currentMonth.format('MMMM YYYY')}
            size="small"
            variant="outlined"
            sx={{ minWidth: 120, fontWeight: 500 }}
          />
          <IconButton size="small" onClick={() => setMonthOffset((o) => Math.max(0, o - 1))} disabled={monthOffset === 0}>
            <ChevronRightIcon fontSize="small" />
          </IconButton>
        </Stack>
      </Box>

      {/* Weekday headers */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 0.5, mb: 0.5 }}>
        {weekDays.map((wd) => (
          <Typography
            key={wd}
            variant="caption"
            sx={{ textAlign: 'center', fontWeight: 600, color: 'text.secondary', fontSize: '0.65rem' }}
          >
            {wd}
          </Typography>
        ))}
      </Box>

      {/* Calendar grid */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 0.5 }}>
        {calendarDays.map((dateStr, idx) => {
          if (!dateStr) {
            return <Box key={`empty-${idx}`} sx={{ aspectRatio: '1', minHeight: 28 }} />;
          }

          const dayData = dayMap[dateStr];
          const total = dayData?.total || 0;
          const intensity = getIntensity(total);
          const isToday = dateStr === dayjs().format('YYYY-MM-DD');
          const dayNum = dayjs(dateStr).date();
          const isFuture = dayjs(dateStr).isAfter(dayjs(), 'day');

          const tooltipText = dayData
            ? `${dayjs(dateStr).format('MMM D')}: ${dayData.meeting_count} meetings, ${dayData.note_count} notes, ${dayData.doc_count} docs`
            : `${dayjs(dateStr).format('MMM D')}: No data`;

          return (
            <Tooltip key={dateStr} title={tooltipText} arrow>
              <Box
                onClick={() => dayData && navigate(`/day/${dateStr}`)}
                sx={{
                  aspectRatio: '1',
                  minHeight: 28,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: 0.5,
                  bgcolor: isFuture ? 'transparent' : colors[intensity],
                  border: isToday ? '2px solid' : '1px solid transparent',
                  borderColor: isToday ? 'primary.main' : 'transparent',
                  cursor: dayData ? 'pointer' : 'default',
                  transition: 'all 0.15s',
                  '&:hover': dayData ? { transform: 'scale(1.1)', boxShadow: 1 } : {},
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    fontSize: '0.7rem',
                    fontWeight: isToday ? 700 : 400,
                    color: intensity >= 3
                      ? 'white'
                      : isToday
                        ? 'primary.main'
                        : isFuture
                          ? 'text.disabled'
                          : 'text.secondary',
                  }}
                >
                  {dayNum}
                </Typography>
              </Box>
            </Tooltip>
          );
        })}
      </Box>

      {/* Legend */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1.5, justifyContent: 'flex-end' }}>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', mr: 0.5 }}>
          Less
        </Typography>
        {colors.map((color, idx) => (
          <Box
            key={idx}
            sx={{
              width: 12,
              height: 12,
              borderRadius: 0.5,
              bgcolor: color,
            }}
          />
        ))}
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem', ml: 0.5 }}>
          More
        </Typography>
      </Box>
    </Paper>
  );
}
