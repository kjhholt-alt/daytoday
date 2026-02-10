import React from 'react';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Chip,
  Box,
  Stack,
  List,
  ListItem,
  ListItemText,
  Link,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Videocam as VideocamIcon,
  LocationOn as LocationIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import TranscriptView from './TranscriptView';

function formatTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function MeetingCard({ meeting }) {
  const startTime = formatTime(meeting.start_time);
  const endTime = formatTime(meeting.end_time);
  const hasTranscripts = meeting.transcripts && meeting.transcripts.length > 0;

  return (
    <Accordion>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%', flexWrap: 'wrap' }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ minWidth: 120 }}>
            {startTime} - {endTime}
          </Typography>
          <Typography variant="subtitle1" sx={{ fontWeight: 'medium', flexGrow: 1 }}>
            {meeting.subject}
          </Typography>
          <Stack direction="row" spacing={0.5}>
            {meeting.is_online_meeting && (
              <Chip icon={<VideocamIcon />} label="Teams" size="small" color="primary" variant="outlined" />
            )}
            {hasTranscripts && (
              <Chip label="Transcript" size="small" color="success" variant="outlined" />
            )}
          </Stack>
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <PersonIcon fontSize="small" color="action" />
            <Typography variant="body2">
              <strong>Organizer:</strong> {meeting.organizer_name}
              {meeting.organizer_email && ` (${meeting.organizer_email})`}
            </Typography>
          </Box>

          {meeting.location && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <LocationIcon fontSize="small" color="action" />
              <Typography variant="body2">{meeting.location}</Typography>
            </Box>
          )}

          {meeting.body_preview && (
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {meeting.body_preview}
              </Typography>
            </Box>
          )}

          {meeting.attendees_json && meeting.attendees_json.length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                Attendees ({meeting.attendees_json.length}):
              </Typography>
              <List dense disablePadding>
                {meeting.attendees_json.slice(0, 15).map((a, idx) => (
                  <ListItem key={idx} disablePadding sx={{ pl: 2 }}>
                    <ListItemText
                      primary={a.name || a.email}
                      secondary={a.response !== 'none' ? a.response : null}
                      primaryTypographyProps={{ variant: 'body2' }}
                      secondaryTypographyProps={{ variant: 'caption' }}
                    />
                  </ListItem>
                ))}
                {meeting.attendees_json.length > 15 && (
                  <ListItem disablePadding sx={{ pl: 2 }}>
                    <ListItemText
                      primary={`...and ${meeting.attendees_json.length - 15} more`}
                      primaryTypographyProps={{ variant: 'body2', color: 'text.secondary' }}
                    />
                  </ListItem>
                )}
              </List>
            </Box>
          )}

          {meeting.online_meeting_url && (
            <Link href={meeting.online_meeting_url} target="_blank" rel="noopener" variant="body2">
              Join Meeting Link
            </Link>
          )}

          {hasTranscripts && meeting.transcripts.map((t) => (
            <TranscriptView key={t.id} transcript={t} />
          ))}
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}
