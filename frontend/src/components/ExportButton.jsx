import React, { useState } from 'react';
import {
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Snackbar,
  Alert,
  Tooltip,
} from '@mui/material';
import {
  FileDownload as ExportIcon,
  ContentCopy as CopyIcon,
  Print as PrintIcon,
} from '@mui/icons-material';
import dayjs from 'dayjs';

function summaryToMarkdown(summary, displayDate) {
  const lines = [];
  lines.push(`# Daily Summary - ${displayDate}`);
  lines.push('');

  if (summary.meetings && summary.meetings.length > 0) {
    lines.push(`## Meetings (${summary.meetings.length})`);
    lines.push('');
    summary.meetings.forEach((m) => {
      const start = dayjs(m.start_time).format('h:mm A');
      const end = dayjs(m.end_time).format('h:mm A');
      lines.push(`### ${m.subject}`);
      lines.push(`- **Time:** ${start} - ${end}`);
      if (m.organizer_name) lines.push(`- **Organizer:** ${m.organizer_name}`);
      if (m.location) lines.push(`- **Location:** ${m.location}`);
      if (m.attendees_json && m.attendees_json.length > 0) {
        const names = m.attendees_json.slice(0, 10).map((a) => a.name || a.email).join(', ');
        const extra = m.attendees_json.length > 10 ? ` (+${m.attendees_json.length - 10} more)` : '';
        lines.push(`- **Attendees (${m.attendees_json.length}):** ${names}${extra}`);
      }
      if (m.body_preview) lines.push(`- **Notes:** ${m.body_preview}`);
      lines.push('');
    });
  }

  if (summary.note_references && summary.note_references.length > 0) {
    lines.push(`## Notes (${summary.note_references.length})`);
    lines.push('');
    summary.note_references.forEach((n) => {
      const path = [n.notebook_name, n.section_name].filter(Boolean).join(' > ');
      lines.push(`- **${n.page_title}** ${path ? `(${path})` : ''}`);
    });
    lines.push('');
  }

  if (summary.word_documents && summary.word_documents.length > 0) {
    lines.push(`## Documents (${summary.word_documents.length})`);
    lines.push('');
    summary.word_documents.forEach((d) => {
      lines.push(`- ${d.file_name}`);
    });
    lines.push('');
  }

  if (summary.action_items && summary.action_items.length > 0) {
    lines.push('## Action Items');
    lines.push('');
    summary.action_items.forEach((item) => {
      const check = item.completed ? 'x' : ' ';
      const priority = item.priority === 'high' ? ' [HIGH]' : item.priority === 'low' ? ' [LOW]' : '';
      lines.push(`- [${check}] ${item.text}${priority}`);
    });
    lines.push('');
  }

  if (summary.summary_text) {
    lines.push('## Summary');
    lines.push('');
    lines.push(summary.summary_text);
  }

  return lines.join('\n');
}

function summaryToHtmlPrint(summary, displayDate) {
  let html = `<!DOCTYPE html>
<html><head><title>Daily Summary - ${displayDate}</title>
<style>
  body { font-family: 'Segoe UI', Tahoma, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; }
  h1 { color: #1565c0; border-bottom: 2px solid #1565c0; padding-bottom: 8px; }
  h2 { color: #444; margin-top: 24px; }
  h3 { margin-bottom: 4px; }
  .meeting { margin-bottom: 16px; padding: 12px; border-left: 3px solid #1565c0; background: #f5f5f5; border-radius: 4px; }
  .meta { color: #666; font-size: 0.9em; margin: 2px 0; }
  .action-item { padding: 4px 0; }
  .action-done { text-decoration: line-through; color: #888; }
  .priority-high { color: #d32f2f; font-weight: bold; }
  ul { padding-left: 20px; }
  @media print { body { padding: 0; } }
</style></head><body>`;

  html += `<h1>Daily Summary - ${displayDate}</h1>`;

  if (summary.meetings && summary.meetings.length > 0) {
    html += `<h2>Meetings (${summary.meetings.length})</h2>`;
    summary.meetings.forEach((m) => {
      const start = dayjs(m.start_time).format('h:mm A');
      const end = dayjs(m.end_time).format('h:mm A');
      html += `<div class="meeting">`;
      html += `<h3>${escapeHtml(m.subject)}</h3>`;
      html += `<p class="meta">${start} - ${end}`;
      if (m.organizer_name) html += ` | Organizer: ${escapeHtml(m.organizer_name)}`;
      if (m.location) html += ` | ${escapeHtml(m.location)}`;
      html += `</p>`;
      if (m.attendees_json && m.attendees_json.length > 0) {
        const names = m.attendees_json.slice(0, 10).map((a) => escapeHtml(a.name || a.email)).join(', ');
        html += `<p class="meta">Attendees (${m.attendees_json.length}): ${names}</p>`;
      }
      if (m.body_preview) html += `<p class="meta">${escapeHtml(m.body_preview)}</p>`;
      html += `</div>`;
    });
  }

  if (summary.note_references && summary.note_references.length > 0) {
    html += `<h2>Notes (${summary.note_references.length})</h2><ul>`;
    summary.note_references.forEach((n) => {
      html += `<li><strong>${escapeHtml(n.page_title)}</strong>`;
      const path = [n.notebook_name, n.section_name].filter(Boolean).join(' > ');
      if (path) html += ` <span class="meta">(${escapeHtml(path)})</span>`;
      html += `</li>`;
    });
    html += `</ul>`;
  }

  if (summary.word_documents && summary.word_documents.length > 0) {
    html += `<h2>Documents (${summary.word_documents.length})</h2><ul>`;
    summary.word_documents.forEach((d) => {
      html += `<li>${escapeHtml(d.file_name)}</li>`;
    });
    html += `</ul>`;
  }

  if (summary.action_items && summary.action_items.length > 0) {
    html += `<h2>Action Items</h2><ul>`;
    summary.action_items.forEach((item) => {
      const cls = item.completed ? 'action-item action-done' : 'action-item';
      const priorityCls = item.priority === 'high' ? ' priority-high' : '';
      const check = item.completed ? '&#9745;' : '&#9744;';
      html += `<li class="${cls}${priorityCls}">${check} ${escapeHtml(item.text)}</li>`;
    });
    html += `</ul>`;
  }

  html += `</body></html>`;
  return html;
}

function escapeHtml(text) {
  if (!text) return '';
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export default function ExportButton({ summary, displayDate }) {
  const [anchorEl, setAnchorEl] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

  if (!summary) return null;

  const handleCopyMarkdown = () => {
    const md = summaryToMarkdown(summary, displayDate);
    navigator.clipboard.writeText(md).then(() => {
      setSnackbar({ open: true, message: 'Summary copied to clipboard as Markdown', severity: 'success' });
    });
    setAnchorEl(null);
  };

  const handlePrint = () => {
    const html = summaryToHtmlPrint(summary, displayDate);
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(html);
      printWindow.document.close();
      printWindow.focus();
      setTimeout(() => printWindow.print(), 250);
    }
    setAnchorEl(null);
  };

  return (
    <>
      <Tooltip title="Export / Print">
        <IconButton size="small" onClick={(e) => setAnchorEl(e.currentTarget)}>
          <ExportIcon />
        </IconButton>
      </Tooltip>

      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
        <MenuItem onClick={handleCopyMarkdown}>
          <ListItemIcon><CopyIcon fontSize="small" /></ListItemIcon>
          <ListItemText>Copy as Markdown</ListItemText>
        </MenuItem>
        <MenuItem onClick={handlePrint}>
          <ListItemIcon><PrintIcon fontSize="small" /></ListItemIcon>
          <ListItemText>Print / Save as PDF</ListItemText>
        </MenuItem>
      </Menu>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar((s) => ({ ...s, open: false }))} variant="filled">
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  );
}
