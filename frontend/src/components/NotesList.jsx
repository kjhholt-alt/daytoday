import React, { useState } from 'react';
import {
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
  Paper,
  Chip,
  Box,
  Collapse,
  IconButton,
  Tooltip,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  Note as NoteIcon,
  FiberNew as NewIcon,
  Update as UpdateIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';
import { openNote } from '../services/api';

function getChangeChip(changeType) {
  if (changeType === 'new') {
    return (
      <Chip
        icon={<NewIcon />}
        label="New"
        size="small"
        color="success"
        variant="outlined"
        sx={{ ml: 1 }}
      />
    );
  }
  if (changeType === 'updated') {
    return (
      <Chip
        icon={<UpdateIcon />}
        label="Updated"
        size="small"
        color="info"
        variant="outlined"
        sx={{ ml: 1 }}
      />
    );
  }
  return null;
}

function NoteItem({ note }) {
  const [expanded, setExpanded] = useState(false);
  const [snack, setSnack] = useState({ open: false, message: '', severity: 'success' });
  const hasContent = note.content_snippet && note.content_snippet.trim().length > 0;

  const handleOpenNote = async (e) => {
    e.stopPropagation();
    try {
      const res = await openNote(note.id);
      if (res.data.action === 'open_url') {
        window.open(res.data.url, '_blank');
      } else {
        setSnack({ open: true, message: res.data.detail || 'Opened in OneNote', severity: 'success' });
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Could not open note';
      setSnack({ open: true, message: msg, severity: 'error' });
    }
  };

  const handleClick = () => {
    if (hasContent) {
      setExpanded(!expanded);
    }
  };

  // Render content lines — clicking opens OneNote
  const renderContentLines = () => {
    if (!note.content_snippet) return null;
    const lines = note.content_snippet.split('\n').filter((l) => l.trim());
    return lines.map((line, i) => (
      <Typography
        key={i}
        variant="body2"
        onClick={(e) => { e.stopPropagation(); handleOpenNote(e); }}
        sx={{
          cursor: 'pointer',
          py: 0.3,
          px: 0.5,
          borderRadius: 0.5,
          fontSize: '0.85rem',
          lineHeight: 1.6,
          '&:hover': {
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
          },
        }}
      >
        {line}
      </Typography>
    ));
  };

  return (
    <>
      <ListItem
        button
        onClick={handleClick}
        sx={{
          py: 0.5,
          alignItems: 'flex-start',
          flexDirection: 'column',
          cursor: hasContent ? 'pointer' : 'default',
          '&:hover': { bgcolor: 'action.hover' },
          borderRadius: 1,
        }}
      >
        <Box sx={{ display: 'flex', width: '100%', alignItems: 'flex-start' }}>
          <ListItemIcon sx={{ minWidth: 36, mt: 0.5 }}>
            <NoteIcon fontSize="small" color="primary" />
          </ListItemIcon>
          <ListItemText
            primary={
              <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  {note.page_title}
                </Typography>
                {getChangeChip(note.change_type)}
                <Tooltip title="Open in OneNote">
                  <IconButton
                    size="small"
                    onClick={handleOpenNote}
                    color="primary"
                    sx={{ ml: 0.5 }}
                  >
                    <OpenInNewIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                {hasContent && (
                  <IconButton size="small" sx={{ ml: 0.5 }}>
                    {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                  </IconButton>
                )}
              </Box>
            }
            secondary={
              <Box component="span" sx={{ display: 'block' }}>
                {[note.notebook_name, note.section_name]
                  .filter(Boolean)
                  .join(' > ') && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    component="span"
                    sx={{ display: 'block' }}
                  >
                    {[note.notebook_name, note.section_name]
                      .filter(Boolean)
                      .join(' > ')}
                  </Typography>
                )}
                {note.changes_summary &&
                  note.change_type !== 'unchanged' && (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      component="span"
                      sx={{
                        display: 'block',
                        mt: 0.5,
                        fontStyle: 'italic',
                      }}
                    >
                      {note.changes_summary.length > 200
                        ? note.changes_summary.substring(0, 200) + '...'
                        : note.changes_summary}
                    </Typography>
                  )}
              </Box>
            }
          />
        </Box>
        {hasContent && (
          <Collapse in={expanded} sx={{ width: '100%', pl: 4.5 }}>
            <Box
              sx={{
                mt: 0.5,
                mb: 1,
                p: 1.5,
                bgcolor: 'action.hover',
                borderRadius: 1,
                borderLeft: 3,
                borderColor: 'primary.main',
                maxHeight: 300,
                overflow: 'auto',
              }}
            >
              {renderContentLines()}
            </Box>
          </Collapse>
        )}
      </ListItem>
      <Snackbar
        open={snack.open}
        autoHideDuration={3000}
        onClose={() => setSnack({ ...snack, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snack.severity} onClose={() => setSnack({ ...snack, open: false })}>
          {snack.message}
        </Alert>
      </Snackbar>
    </>
  );
}

export default function NotesList({ notes }) {
  if (!notes || notes.length === 0) return null;

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        OneNote Pages ({notes.length})
      </Typography>
      <List dense>
        {notes.map((note) => (
          <NoteItem key={note.id} note={note} />
        ))}
      </List>
    </Paper>
  );
}
