import React, { useState } from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import { Description as TranscriptIcon } from '@mui/icons-material';

export default function TranscriptView({ transcript }) {
  const [expanded, setExpanded] = useState(false);
  const content = transcript.content_plain || transcript.content_vtt || '';
  const preview = content.slice(0, 500);
  const isLong = content.length > 500;

  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 1, bgcolor: 'grey.50' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <TranscriptIcon fontSize="small" color="success" />
        <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
          Meeting Transcript
        </Typography>
      </Box>
      <Typography
        variant="body2"
        component="pre"
        sx={{
          whiteSpace: 'pre-wrap',
          fontFamily: 'monospace',
          fontSize: '0.8rem',
          maxHeight: expanded ? 'none' : 200,
          overflow: 'hidden',
        }}
      >
        {expanded ? content : preview}
        {!expanded && isLong && '...'}
      </Typography>
      {isLong && (
        <Button size="small" onClick={() => setExpanded(!expanded)} sx={{ mt: 1 }}>
          {expanded ? 'Show Less' : 'Show Full Transcript'}
        </Button>
      )}
    </Paper>
  );
}
