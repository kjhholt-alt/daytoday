import React from 'react';
import {
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
  Paper,
  Link,
  Chip,
  Box,
} from '@mui/material';
import {
  Note as NoteIcon,
  FiberNew as NewIcon,
  Update as UpdateIcon,
} from '@mui/icons-material';

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

export default function NotesList({ notes }) {
  if (!notes || notes.length === 0) return null;

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        OneNote Pages ({notes.length})
      </Typography>
      <List dense>
        {notes.map((note) => (
          <ListItem
            key={note.id}
            disablePadding
            sx={{ py: 0.5, alignItems: 'flex-start' }}
          >
            <ListItemIcon sx={{ minWidth: 36, mt: 0.5 }}>
              <NoteIcon fontSize="small" color="primary" />
            </ListItemIcon>
            <ListItemText
              primary={
                <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                  {note.web_url ? (
                    <Link href={note.web_url} target="_blank" rel="noopener">
                      {note.page_title}
                    </Link>
                  ) : (
                    note.page_title
                  )}
                  {getChangeChip(note.change_type)}
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
                          whiteSpace: 'pre-line',
                          maxHeight: 60,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {note.changes_summary.length > 200
                          ? note.changes_summary.substring(0, 200) + '...'
                          : note.changes_summary}
                      </Typography>
                    )}
                  {note.change_type === 'new' &&
                    !note.changes_summary &&
                    note.content_snippet && (
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        component="span"
                        sx={{
                          display: 'block',
                          mt: 0.5,
                          fontStyle: 'italic',
                          whiteSpace: 'pre-line',
                          maxHeight: 60,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {note.content_snippet.length > 200
                          ? note.content_snippet.substring(0, 200) + '...'
                          : note.content_snippet}
                      </Typography>
                    )}
                </Box>
              }
            />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
}
