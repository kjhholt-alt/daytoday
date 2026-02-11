import React, { useEffect, useRef } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Typography,
  Box,
} from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';

/**
 * Full-screen dialog that shows the complete OneNote page content,
 * auto-scrolling to and highlighting a specific search term.
 */
export default function NoteDetailDialog({ open, onClose, note, highlightText }) {
  const contentRef = useRef(null);

  useEffect(() => {
    if (open && highlightText && contentRef.current) {
      // Wait for dialog to render, then scroll to first highlight
      const timer = setTimeout(() => {
        const mark = contentRef.current.querySelector('mark');
        if (mark) {
          mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [open, highlightText]);

  if (!note) return null;

  const fullText = note.content_text || note.content_snippet || '';

  // Build highlighted content
  const renderContent = () => {
    if (!highlightText || !fullText) {
      return (
        <Typography
          variant="body2"
          sx={{ whiteSpace: 'pre-line', lineHeight: 1.8, fontSize: '0.9rem' }}
        >
          {fullText || 'No content available.'}
        </Typography>
      );
    }

    // Split text around the highlight term (case-insensitive)
    const parts = [];
    const lowerText = fullText.toLowerCase();
    const lowerHighlight = highlightText.toLowerCase();
    let lastIndex = 0;

    let idx = lowerText.indexOf(lowerHighlight, lastIndex);
    while (idx !== -1) {
      if (idx > lastIndex) {
        parts.push({ text: fullText.slice(lastIndex, idx), highlight: false });
      }
      parts.push({ text: fullText.slice(idx, idx + highlightText.length), highlight: true });
      lastIndex = idx + highlightText.length;
      idx = lowerText.indexOf(lowerHighlight, lastIndex);
    }
    if (lastIndex < fullText.length) {
      parts.push({ text: fullText.slice(lastIndex), highlight: false });
    }

    return (
      <Typography
        variant="body2"
        component="div"
        sx={{ whiteSpace: 'pre-line', lineHeight: 1.8, fontSize: '0.9rem' }}
      >
        {parts.map((part, i) =>
          part.highlight ? (
            <mark
              key={i}
              style={{
                backgroundColor: '#ffe082',
                padding: '1px 2px',
                borderRadius: 2,
              }}
            >
              {part.text}
            </mark>
          ) : (
            <span key={i}>{part.text}</span>
          )
        )}
      </Typography>
    );
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{ sx: { height: '80vh' } }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1, pr: 6 }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6">{note.page_title}</Typography>
          {(note.notebook_name || note.section_name) && (
            <Typography variant="caption" color="text.secondary">
              {[note.notebook_name, note.section_name].filter(Boolean).join(' > ')}
            </Typography>
          )}
        </Box>
        <IconButton
          onClick={onClose}
          sx={{ position: 'absolute', right: 8, top: 8 }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers ref={contentRef}>
        {renderContent()}
      </DialogContent>
    </Dialog>
  );
}
