import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Stack,
  Paper,
  IconButton,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Divider,
  Tooltip,
  Alert,
} from '@mui/material';
import {
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  CalendarMonth as CalendarIcon,
  AccessTime as TimeIcon,
  Group as GroupIcon,
  Note as NoteIcon,
  Description as DocIcon,
  CheckCircle as CheckIcon,
  TrendingUp as TrendingUpIcon,
} from '@mui/icons-material';
import dayjs from 'dayjs';
import { getWeeklyRecap } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';

function formatHours(totalMinutes) {
  if (totalMinutes === 0) return '0h';
  const hours = Math.floor(totalMinutes / 60);
  const mins = totalMinutes % 60;
  if (hours === 0) return `${mins}m`;
  if (mins === 0) return `${hours}h`;
  return `${hours}h ${mins}m`;
}

function stringToColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return `hsl(${Math.abs(hash % 360)}, 55%, 50%)`;
}

function getInitials(name) {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0][0].toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// Simple CSS bar chart - no external charting library needed
function MeetingHoursChart({ days }) {
  const maxMinutes = Math.max(...days.map((d) => d.meeting_minutes), 60);

  return (
    <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 1, height: 140, pt: 2 }}>
      {days.map((day) => {
        const height = day.meeting_minutes > 0
          ? Math.max((day.meeting_minutes / maxMinutes) * 110, 4)
          : 2;
        const isToday = dayjs(day.date).isSame(dayjs(), 'day');
        const isWeekend = [0, 6].includes(dayjs(day.date).day());

        return (
          <Tooltip
            key={day.date}
            title={`${day.weekday}: ${day.meeting_count} meetings, ${formatHours(day.meeting_minutes)}`}
          >
            <Box
              sx={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 0.5,
              }}
            >
              {day.meeting_minutes > 0 && (
                <Typography variant="caption" sx={{ fontSize: '0.65rem', fontWeight: 600 }}>
                  {formatHours(day.meeting_minutes)}
                </Typography>
              )}
              <Box
                sx={{
                  width: '100%',
                  maxWidth: 48,
                  height,
                  borderRadius: '4px 4px 0 0',
                  bgcolor: !day.has_data
                    ? 'action.disabledBackground'
                    : isToday
                      ? 'primary.main'
                      : isWeekend
                        ? 'action.selected'
                        : 'primary.light',
                  opacity: isWeekend && !day.has_data ? 0.3 : 1,
                  transition: 'height 0.3s ease',
                }}
              />
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.7rem',
                  fontWeight: isToday ? 700 : 400,
                  color: isToday ? 'primary.main' : 'text.secondary',
                }}
              >
                {day.weekday.slice(0, 3)}
              </Typography>
            </Box>
          </Tooltip>
        );
      })}
    </Box>
  );
}

function StatCard({ icon, label, value, subtitle, color = 'primary.main' }) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        flex: 1,
        minWidth: 130,
        textAlign: 'center',
      }}
    >
      <Box sx={{ color, mb: 0.5 }}>{icon}</Box>
      <Typography variant="h5" sx={{ fontWeight: 700, color }}>
        {value}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 500 }}>
        {label}
      </Typography>
      {subtitle && (
        <Typography variant="caption" color="text.secondary">
          {subtitle}
        </Typography>
      )}
    </Paper>
  );
}

export default function WeeklyRecap() {
  const navigate = useNavigate();
  const [weekDate, setWeekDate] = useState(dayjs().format('YYYY-MM-DD'));
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getWeeklyRecap(weekDate);
        setData(res.data);
      } catch (err) {
        setError('Failed to load weekly recap.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [weekDate]);

  const goToPrevWeek = () => {
    setWeekDate(dayjs(weekDate).subtract(7, 'day').format('YYYY-MM-DD'));
  };

  const goToNextWeek = () => {
    setWeekDate(dayjs(weekDate).add(7, 'day').format('YYYY-MM-DD'));
  };

  const goToThisWeek = () => {
    setWeekDate(dayjs().format('YYYY-MM-DD'));
  };

  const isCurrentWeek = useMemo(() => {
    if (!data) return false;
    const today = dayjs().format('YYYY-MM-DD');
    return today >= data.week_start && today <= data.week_end;
  }, [data]);

  if (loading) return <LoadingSpinner message="Loading weekly recap..." />;

  const weekLabel = data
    ? `${dayjs(data.week_start).format('MMM D')} - ${dayjs(data.week_end).format('MMM D, YYYY')}`
    : '';

  const totals = data?.totals || {};
  const daysWithData = (data?.days || []).filter((d) => d.has_data).length;
  const avgMeetingsPerDay = daysWithData > 0
    ? (totals.meetings / daysWithData).toFixed(1)
    : 0;

  return (
    <Stack spacing={3}>
      {/* Header with week navigation */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <TrendingUpIcon color="primary" />
          <Typography variant="h5">Weekly Recap</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton onClick={goToPrevWeek} size="small">
            <ChevronLeftIcon />
          </IconButton>
          <Chip
            label={weekLabel}
            variant={isCurrentWeek ? 'filled' : 'outlined'}
            color={isCurrentWeek ? 'primary' : 'default'}
            onClick={isCurrentWeek ? undefined : goToThisWeek}
            sx={{ fontWeight: 600, minWidth: 180 }}
          />
          <IconButton onClick={goToNextWeek} size="small" disabled={isCurrentWeek}>
            <ChevronRightIcon />
          </IconButton>
        </Box>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      {data && (
        <>
          {/* Summary stats row */}
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <StatCard
              icon={<CalendarIcon />}
              label="Meetings"
              value={totals.meetings}
              subtitle={`avg ${avgMeetingsPerDay}/day`}
            />
            <StatCard
              icon={<TimeIcon />}
              label="In Meetings"
              value={formatHours(totals.meeting_minutes)}
              subtitle={daysWithData > 0 ? `${formatHours(Math.round(totals.meeting_minutes / daysWithData))}/day avg` : null}
              color="secondary.main"
            />
            <StatCard
              icon={<GroupIcon />}
              label="Collaborators"
              value={totals.unique_collaborators}
              color="success.main"
            />
            <StatCard
              icon={<NoteIcon />}
              label="Notes"
              value={totals.notes}
            />
            <StatCard
              icon={<DocIcon />}
              label="Documents"
              value={totals.documents}
            />
            {totals.action_items > 0 && (
              <StatCard
                icon={<CheckIcon />}
                label="Action Items"
                value={`${totals.completed_action_items}/${totals.action_items}`}
                subtitle="completed"
                color={totals.completed_action_items === totals.action_items ? 'success.main' : 'warning.main'}
              />
            )}
          </Box>

          {/* Meeting hours bar chart */}
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Meeting Hours by Day
            </Typography>
            <MeetingHoursChart days={data.days} />
          </Paper>

          {/* Day-by-day breakdown */}
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Day-by-Day
            </Typography>
            <List>
              {(data.days || []).map((day, idx) => {
                const isToday = dayjs(day.date).isSame(dayjs(), 'day');
                return (
                  <React.Fragment key={day.date}>
                    <ListItem
                      sx={{
                        cursor: day.has_data ? 'pointer' : 'default',
                        borderRadius: 1,
                        bgcolor: isToday ? 'action.selected' : 'transparent',
                        '&:hover': day.has_data ? { bgcolor: 'action.hover' } : {},
                      }}
                      onClick={() => day.has_data && navigate(`/day/${day.date}`)}
                    >
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body1" sx={{ fontWeight: isToday ? 700 : 500, minWidth: 100 }}>
                              {day.weekday}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ minWidth: 80 }}>
                              {dayjs(day.date).format('MMM D')}
                            </Typography>
                            {day.has_data ? (
                              <Stack direction="row" spacing={0.5}>
                                {day.meeting_count > 0 && (
                                  <Chip
                                    icon={<CalendarIcon sx={{ fontSize: 14 }} />}
                                    label={`${day.meeting_count} mtg${day.meeting_count !== 1 ? 's' : ''}`}
                                    size="small"
                                    variant="outlined"
                                    sx={{ height: 22, fontSize: '0.7rem' }}
                                  />
                                )}
                                {day.meeting_minutes > 0 && (
                                  <Chip
                                    icon={<TimeIcon sx={{ fontSize: 14 }} />}
                                    label={formatHours(day.meeting_minutes)}
                                    size="small"
                                    variant="outlined"
                                    sx={{ height: 22, fontSize: '0.7rem' }}
                                  />
                                )}
                                {day.note_count > 0 && (
                                  <Chip
                                    icon={<NoteIcon sx={{ fontSize: 14 }} />}
                                    label={day.note_count}
                                    size="small"
                                    variant="outlined"
                                    sx={{ height: 22, fontSize: '0.7rem' }}
                                  />
                                )}
                                {day.doc_count > 0 && (
                                  <Chip
                                    icon={<DocIcon sx={{ fontSize: 14 }} />}
                                    label={day.doc_count}
                                    size="small"
                                    variant="outlined"
                                    sx={{ height: 22, fontSize: '0.7rem' }}
                                  />
                                )}
                              </Stack>
                            ) : (
                              <Typography variant="body2" color="text.disabled">
                                No data
                              </Typography>
                            )}
                            {isToday && (
                              <Chip label="Today" size="small" color="primary" sx={{ height: 20, fontSize: '0.65rem' }} />
                            )}
                          </Box>
                        }
                      />
                    </ListItem>
                    {idx < data.days.length - 1 && <Divider component="li" />}
                  </React.Fragment>
                );
              })}
            </List>
          </Paper>

          {/* Top collaborators this week */}
          {data.top_collaborators && data.top_collaborators.length > 0 && (
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Top Collaborators This Week
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {data.top_collaborators.map((person, idx) => (
                  <Chip
                    key={idx}
                    avatar={
                      <Avatar sx={{ bgcolor: stringToColor(person.name || person.email) }}>
                        {getInitials(person.name || person.email)}
                      </Avatar>
                    }
                    label={`${person.name || person.email} (${person.count})`}
                    variant="outlined"
                    onClick={() => navigate(`/people?q=${encodeURIComponent(person.name || person.email)}`)}
                    sx={{ cursor: 'pointer' }}
                  />
                ))}
              </Box>
            </Paper>
          )}
        </>
      )}
    </Stack>
  );
}
