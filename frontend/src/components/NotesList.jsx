import React from 'react';
import {
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
  Paper,
  Link,
} from '@mui/material';
import { Note as NoteIcon } from '@mui/icons-material';

export default function NotesList({ notes }) {
  if (!notes || notes.length === 0) return null;

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        OneNote Pages ({notes.length})
      </Typography>
      <List dense>
        {notes.map((note) => (
          <ListItem key={note.id} disablePadding sx={{ py: 0.5 }}>
            <ListItemIcon sx={{ minWidth: 36 }}>
              <NoteIcon fontSize="small" color="primary" />
            </ListItemIcon>
            <ListItemText
              primary={
                note.web_url ? (
                  <Link href={note.web_url} target="_blank" rel="noopener">
                    {note.page_title}
                  </Link>
                ) : (
                  note.page_title
                )
              }
              secondary={
                [note.notebook_name, note.section_name].filter(Boolean).join(' > ') || null
              }
            />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
}
