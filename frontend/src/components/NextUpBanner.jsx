import React, { useState, useEffect, useMemo } from 'react';
import {
  Paper,
  Typography,
  Box,
  Button,
  Chip,
  Stack,
} from '@mui/material';
import {
  Videocam as VideocamIcon,
  Schedule as ScheduleIcon,
  OpenInNew as OpenInNewIcon,
  Group as GroupIcon,
} from '@mui/icons-material';
import dayjs from 'dayjs';

function getCountdownText(startTime) {
  const now = dayjs();
  const start = dayjs(startTime);
  const diffMinutes = start.diff(now, 'minute');

  if (diffMinutes <= 0) return 'Starting now';
  if (diffMinutes === 1) return 'Starting in 1 minute';
  if (diffMinutes < 60) return `Starting in ${diffMinutes} minutes`;

  const hours = Math.floor(diffMinutes / 60);
  const mins = diffMinutes % 60;
  if (mins === 0) {
    return hours === 1 ? 'Starting in 1 hour' : `Starting in ${hours} hours`;
  }
  return hours === 1
    ? `Starting in 1 hr ${mins} min`
    : `Starting in ${hours} hrs ${mins} min`;
}

function isBusinessHours() {
  const now = dayjs();
  const hour = now.hour();
  const day = now.day(); // 0=Sunday, 6=Saturday
  return day >= 1 && day <= 5 && hour >= 7 && hour <= 19;
}

export default function NextUpBanner({ meetings }) {
  const [now, setNow] = useState(dayjs());

  // Tick every 60 seconds to update countdown
  useEffect(() => {
    const interval = setInterval(() => {
      setNow(dayjs());
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  const nextMeeting = useMemo(() => {
    if (!meetings || meetings.length === 0) return null;
    const currentTime = now;
    // Find the next upcoming meeting (start_time is in the future)
    const upcoming = meetings
      .filter((m) => dayjs(m.start_time).isAfter(currentTime))
      .sort((a, b) => dayjs(a.start_time).diff(dayjs(b.start_time)));
    return upcoming.length > 0 ? upcoming[0] : null;
  }, [meetings, now]);

  // Only show during business hours and when there is a next meeting
  if (!isBusinessHours() || !nextMeeting) return null;

  const countdown = getCountdownText(nextMeeting.start_time);
  const startFormatted = dayjs(nextMeeting.start_time).format('h:mm A');
  const endFormatted = dayjs(nextMeeting.end_time).format('h:mm A');
  const attendeeCount = nextMeeting.attendees_json?.length || 0;
  const diffMinutes = dayjs(nextMeeting.start_time).diff(now, 'minute');
  const isImminent = diffMinutes <= 5;

  return (
    <Paper
      elevation={isImminent ? 4 : 2}
      sx={{
        p: 2,
        mb: 2,
        borderLeft: 4,
        borderColor: isImminent ? 'warning.main' : 'primary.main',
        bgcolor: (theme) =>
          theme.palette.mode === 'dark'
            ? isImminent
              ? 'rgba(255, 167, 38, 0.08)'
              : 'rgba(66, 165, 245, 0.08)'
            : isImminent
              ? 'rgba(255, 167, 38, 0.05)'
              : 'rgba(66, 165, 245, 0.05)',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1 }}>
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
            <ScheduleIcon fontSize="small" color={isImminent ? 'warning' : 'primary'} />
            <Typography
              variant="caption"
              sx={{
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: 0.5,
                color: isImminent ? 'warning.main' : 'primary.main',
              }}
            >
              Next Up
            </Typography>
            <Chip
              label={countdown}
              size="small"
              color={isImminent ? 'warning' : 'primary'}
              variant={isImminent ? 'filled' : 'outlined'}
              sx={{ fontWeight: 600, fontSize: '0.7rem', height: 22 }}
            />
          </Stack>

          <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5 }} noWrap>
            {nextMeeting.subject}
          </Typography>

          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            <Typography variant="body2" color="text.secondary">
              {startFormatted} - {endFormatted}
            </Typography>
            {attendeeCount > 0 && (
              <Chip
                icon={<GroupIcon sx={{ fontSize: 14 }} />}
                label={`${attendeeCount} attendees`}
                size="small"
                variant="outlined"
                sx={{ fontSize: '0.7rem', height: 20 }}
              />
            )}
            {nextMeeting.organizer_name && (
              <Typography variant="body2" color="text.secondary">
                by {nextMeeting.organizer_name}
              </Typography>
            )}
          </Stack>
        </Box>

        {nextMeeting.is_online_meeting && nextMeeting.online_meeting_url && (
          <Button
            variant={isImminent ? 'contained' : 'outlined'}
            color={isImminent ? 'warning' : 'primary'}
            size="small"
            startIcon={<VideocamIcon />}
            endIcon={<OpenInNewIcon sx={{ fontSize: 14 }} />}
            href={nextMeeting.online_meeting_url}
            target="_blank"
            rel="noopener noreferrer"
            sx={{ whiteSpace: 'nowrap', flexShrink: 0 }}
          >
            Join Meeting
          </Button>
        )}
      </Box>
    </Paper>
  );
}
