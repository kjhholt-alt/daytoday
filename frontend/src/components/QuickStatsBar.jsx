import React, { useMemo } from 'react';
import { Chip, Stack } from '@mui/material';
import {
  CalendarMonth as CalendarIcon,
  Note as NoteIcon,
  Description as DocIcon,
  AccessTime as TimeIcon,
} from '@mui/icons-material';
import dayjs from 'dayjs';

function calculateTotalMeetingHours(meetings) {
  if (!meetings || meetings.length === 0) return 0;
  let totalMinutes = 0;
  meetings.forEach((m) => {
    if (m.start_time && m.end_time) {
      totalMinutes += dayjs(m.end_time).diff(dayjs(m.start_time), 'minute');
    }
  });
  return totalMinutes;
}

function formatHours(totalMinutes) {
  if (totalMinutes === 0) return '0 hrs';
  const hours = Math.floor(totalMinutes / 60);
  const mins = totalMinutes % 60;
  if (hours === 0) return `${mins} min`;
  if (mins === 0) return hours === 1 ? '1 hr' : `${hours} hrs`;
  return `${hours}h ${mins}m`;
}

export default function QuickStatsBar({ meetings, notes, documents }) {
  const meetingCount = meetings?.length || 0;
  const noteCount = notes?.length || 0;
  const docCount = documents?.length || 0;

  const totalMeetingTime = useMemo(
    () => formatHours(calculateTotalMeetingHours(meetings)),
    [meetings]
  );

  // Only render if there's anything to show
  if (meetingCount === 0 && noteCount === 0 && docCount === 0) return null;

  return (
    <Stack
      direction="row"
      spacing={1}
      sx={{ flexWrap: 'wrap', gap: 0.5 }}
    >
      {meetingCount > 0 && (
        <Chip
          icon={<CalendarIcon sx={{ fontSize: 16 }} />}
          label={`${meetingCount} Meeting${meetingCount !== 1 ? 's' : ''}`}
          size="small"
          variant="outlined"
          sx={{ fontWeight: 500 }}
        />
      )}
      {meetingCount > 0 && (
        <Chip
          icon={<TimeIcon sx={{ fontSize: 16 }} />}
          label={totalMeetingTime}
          size="small"
          variant="outlined"
          sx={{ fontWeight: 500 }}
        />
      )}
      {noteCount > 0 && (
        <Chip
          icon={<NoteIcon sx={{ fontSize: 16 }} />}
          label={`${noteCount} Note${noteCount !== 1 ? 's' : ''}`}
          size="small"
          variant="outlined"
          sx={{ fontWeight: 500 }}
        />
      )}
      {docCount > 0 && (
        <Chip
          icon={<DocIcon sx={{ fontSize: 16 }} />}
          label={`${docCount} Document${docCount !== 1 ? 's' : ''}`}
          size="small"
          variant="outlined"
          sx={{ fontWeight: 500 }}
        />
      )}
    </Stack>
  );
}
