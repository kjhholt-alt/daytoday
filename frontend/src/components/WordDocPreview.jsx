import React, { useState } from 'react';
import {
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
  Paper,
  Collapse,
  IconButton,
  Box,
} from '@mui/material';
import {
  Description as DocIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';

function DocItem({ doc }) {
  const [open, setOpen] = useState(false);
  const sizeKb = (doc.size_bytes / 1024).toFixed(1);

  return (
    <>
      <ListItem
        disablePadding
        sx={{ py: 0.5 }}
        secondaryAction={
          doc.content_text && (
            <IconButton edge="end" size="small" onClick={() => setOpen(!open)}>
              {open ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          )
        }
      >
        <ListItemIcon sx={{ minWidth: 36 }}>
          <DocIcon fontSize="small" color="info" />
        </ListItemIcon>
        <ListItemText
          primary={doc.file_name}
          secondary={`${sizeKb} KB`}
        />
      </ListItem>
      {doc.content_text && (
        <Collapse in={open}>
          <Box sx={{ pl: 6, pr: 2, pb: 1 }}>
            <Typography
              variant="body2"
              component="pre"
              sx={{
                whiteSpace: 'pre-wrap',
                fontFamily: 'monospace',
                fontSize: '0.75rem',
                maxHeight: 300,
                overflow: 'auto',
                bgcolor: 'grey.50',
                p: 1,
                borderRadius: 1,
              }}
            >
              {doc.content_text.slice(0, 2000)}
              {doc.content_text.length > 2000 && '\n\n... (truncated)'}
            </Typography>
          </Box>
        </Collapse>
      )}
    </>
  );
}

export default function WordDocPreview({ documents }) {
  if (!documents || documents.length === 0) return null;

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Word Documents ({documents.length})
      </Typography>
      <List dense>
        {documents.map((doc) => (
          <DocItem key={doc.id} doc={doc} />
        ))}
      </List>
    </Paper>
  );
}
