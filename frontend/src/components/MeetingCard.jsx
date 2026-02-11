import React, { useState, useEffect } from 'react';
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
  IconButton,
  Tooltip,
  Snackbar,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Videocam as VideocamIcon,
  LocationOn as LocationIcon,
  Person as PersonIcon,
  ContentCopy as ContentCopyIcon,
  OpenInNew as OpenInNewIcon,
  Group as GroupIcon,
  AccessTime as AccessTimeIcon,
  CheckCircleOutline as AcceptedIcon,
  HelpOutline as TentativeIcon,
  CancelOutlined as DeclinedIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import TranscriptView from './TranscriptView';

function formatTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function getMeetingDuration(startStr, endStr) {
  if (!startStr || !endStr) return null;
  const start = dayjs(startStr);
  const end = dayjs(endStr);
  const totalMinutes = end.diff(start, 'minute');
  if (totalMinutes < 60) return `${totalMinutes} min`;
  const hours = Math.floor(totalMinutes / 60);
  const mins = totalMinutes % 60;
  if (mins === 0) return hours === 1 ? '1 hr' : `${hours} hrs`;
  return `${hours} hr ${mins} min`;
}

function getMeetingStatus(startStr, endStr) {
  if (!startStr || !endStr) return null;
  const now = dayjs();
  const start = dayjs(startStr);
  const end = dayjs(endStr);

  if (now.isBefore(start)) {
    return { label: 'Upcoming', color: 'info' };
  }
  if (now.isAfter(end)) {
    return { label: 'Completed', color: 'default' };
  }
  return { label: 'In Progress', color: 'success' };
}

function getUserResponse(attendeesJson) {
  if (!attendeesJson || attendeesJson.length === 0) return null;
  // The current user is typically the organizer or the one with a 'self' flag.
  // Graph API attendees have type/response. Look for common indicators.
  // Typically Graph API marks the user's response. Check for response values.
  const selfAttendee = attendeesJson.find(
    (a) => a.type === 'self' || a.is_self === true
  );
  if (selfAttendee && selfAttendee.response) {
    return selfAttendee.response;
  }
  // If there's no explicit self marker, check if there is a response field
  // on the first attendee (sometimes the user is listed first)
  return null;
}

const responseConfig = {
  accepted: { label: 'Accepted', icon: <AcceptedIcon sx={{ fontSize: 14 }} />, color: 'success' },
  tentativelyAccepted: { label: 'Tentative', icon: <TentativeIcon sx={{ fontSize: 14 }} />, color: 'warning' },
  tentative: { label: 'Tentative', icon: <TentativeIcon sx={{ fontSize: 14 }} />, color: 'warning' },
  declined: { label: 'Declined', icon: <DeclinedIcon sx={{ fontSize: 14 }} />, color: 'error' },
};

export default function MeetingCard({ meeting }) {
  const navigate = useNavigate();
  const startTime = formatTime(meeting.start_time);
  const endTime = formatTime(meeting.end_time);
  const hasTranscripts = meeting.transcripts && meeting.transcripts.length > 0;
  const duration = getMeetingDuration(meeting.start_time, meeting.end_time);
  const attendeeCount = meeting.attendees_json?.length || 0;
  const userResponse = getUserResponse(meeting.attendees_json);
  const responseInfo = userResponse ? responseConfig[userResponse] : null;

  const [meetingStatus, setMeetingStatus] = useState(
    getMeetingStatus(meeting.start_time, meeting.end_time)
  );
  const [copySnackOpen, setCopySnackOpen] = useState(false);

  // Update meeting status every 60 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setMeetingStatus(getMeetingStatus(meeting.start_time, meeting.end_time));
    }, 60000);
    return () => clearInterval(interval);
  }, [meeting.start_time, meeting.end_time]);

  const handleCopyLink = (e) => {
    e.stopPropagation();
    if (meeting.online_meeting_url) {
      navigator.clipboard.writeText(meeting.online_meeting_url).then(() => {
        setCopySnackOpen(true);
      });
    }
  };

  const handleJoinMeeting = (e) => {
    e.stopPropagation();
    if (meeting.online_meeting_url) {
      window.open(meeting.online_meeting_url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <>
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%', flexWrap: 'wrap' }}>
            <Typography variant="subtitle2" color="text.secondary" sx={{ minWidth: 120 }}>
              {startTime} - {endTime}
            </Typography>
            <Typography variant="subtitle1" sx={{ fontWeight: 'medium', flexGrow: 1 }}>
              {meeting.subject}
            </Typography>
            <Stack direction="row" spacing={0.5} alignItems="center" sx={{ flexWrap: 'wrap' }}>
              {/* Meeting status indicator */}
              {meetingStatus && (
                <Chip
                  label={meetingStatus.label}
                  size="small"
                  color={meetingStatus.color}
                  variant={meetingStatus.label === 'Completed' ? 'outlined' : 'filled'}
                  sx={{ fontWeight: 500, fontSize: '0.7rem', height: 22 }}
                />
              )}

              {/* User response status */}
              {responseInfo && (
                <Chip
                  icon={responseInfo.icon}
                  label={responseInfo.label}
                  size="small"
                  color={responseInfo.color}
                  variant="outlined"
                  sx={{ fontSize: '0.7rem', height: 22 }}
                />
              )}

              {/* Duration */}
              {duration && (
                <Chip
                  icon={<AccessTimeIcon sx={{ fontSize: 14 }} />}
                  label={duration}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: '0.7rem', height: 22 }}
                />
              )}

              {/* Attendee count */}
              {attendeeCount > 0 && (
                <Chip
                  icon={<GroupIcon sx={{ fontSize: 14 }} />}
                  label={attendeeCount}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: '0.7rem', height: 22 }}
                />
              )}

              {/* Online meeting indicator */}
              {meeting.is_online_meeting && (
                <Chip icon={<VideocamIcon />} label="Teams" size="small" color="primary" variant="outlined" sx={{ height: 22 }} />
              )}

              {/* Transcript indicator */}
              {hasTranscripts && (
                <Chip label="Transcript" size="small" color="success" variant="outlined" sx={{ height: 22 }} />
              )}

              {/* Quick action buttons */}
              {meeting.is_online_meeting && meeting.online_meeting_url && (
                <>
                  <Tooltip title="Join Meeting">
                    <IconButton
                      size="small"
                      color="primary"
                      onClick={handleJoinMeeting}
                      sx={{ ml: 0.5 }}
                    >
                      <OpenInNewIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Copy Meeting Link">
                    <IconButton
                      size="small"
                      onClick={handleCopyLink}
                    >
                      <ContentCopyIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </>
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
                        primary={
                          <Link
                            component="button"
                            variant="body2"
                            onClick={() => navigate(`/people?q=${encodeURIComponent(a.name || a.email)}`)}
                            sx={{ textAlign: 'left', cursor: 'pointer' }}
                          >
                            {a.name || a.email}
                          </Link>
                        }
                        secondary={a.response !== 'none' ? a.response : null}
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

      <Snackbar
        open={copySnackOpen}
        autoHideDuration={2000}
        onClose={() => setCopySnackOpen(false)}
        message="Meeting link copied to clipboard"
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </>
  );
}
