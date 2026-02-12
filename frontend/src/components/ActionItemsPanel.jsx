import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  TextField,
  Checkbox,
  Chip,
  Stack,
  Collapse,
  Menu,
  MenuItem,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Flag as FlagIcon,
  CheckCircleOutline as CheckCircleOutlineIcon,
  RadioButtonUnchecked as UncheckedIcon,
} from '@mui/icons-material';
import { createActionItem, updateActionItem, deleteActionItem } from '../services/api';

const PRIORITY_CONFIG = {
  high: { label: 'High', color: 'error' },
  medium: { label: 'Medium', color: 'warning' },
  low: { label: 'Low', color: 'default' },
};

export default function ActionItemsPanel({ summaryId, meetingId, items = [], onUpdate }) {
  const [expanded, setExpanded] = useState(true);
  const [newText, setNewText] = useState('');
  const [adding, setAdding] = useState(false);
  const [priorityAnchor, setPriorityAnchor] = useState(null);
  const [editingPriorityId, setEditingPriorityId] = useState(null);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newText.trim() || !summaryId) return;
    setAdding(true);
    try {
      await createActionItem({
        daily_summary: summaryId,
        meeting: meetingId || null,
        text: newText.trim(),
        priority: 'medium',
      });
      setNewText('');
      onUpdate?.();
    } catch (err) {
      console.error('Failed to add action item:', err);
    } finally {
      setAdding(false);
    }
  };

  const handleToggle = async (item) => {
    try {
      await updateActionItem(item.id, { completed: !item.completed });
      onUpdate?.();
    } catch (err) {
      console.error('Failed to update action item:', err);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteActionItem(id);
      onUpdate?.();
    } catch (err) {
      console.error('Failed to delete action item:', err);
    }
  };

  const handlePriorityChange = async (id, priority) => {
    try {
      await updateActionItem(id, { priority });
      setPriorityAnchor(null);
      setEditingPriorityId(null);
      onUpdate?.();
    } catch (err) {
      console.error('Failed to update priority:', err);
    }
  };

  const openItems = items.filter((i) => !i.completed);
  const doneItems = items.filter((i) => i.completed);
  const total = items.length;
  const doneCount = doneItems.length;

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Box
        sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
        onClick={() => setExpanded(!expanded)}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h6" sx={{ fontSize: '1rem' }}>
            Action Items
          </Typography>
          {total > 0 && (
            <Chip
              label={`${doneCount}/${total}`}
              size="small"
              color={doneCount === total ? 'success' : 'default'}
              variant="outlined"
              sx={{ height: 22, fontSize: '0.75rem' }}
            />
          )}
        </Box>
        <IconButton size="small">
          {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </IconButton>
      </Box>

      <Collapse in={expanded}>
        {/* Add new item form */}
        <Box component="form" onSubmit={handleAdd} sx={{ display: 'flex', gap: 1, mt: 1.5, mb: 1 }}>
          <TextField
            size="small"
            fullWidth
            placeholder="Add an action item..."
            value={newText}
            onChange={(e) => setNewText(e.target.value)}
            disabled={adding || !summaryId}
            sx={{ '& .MuiInputBase-root': { fontSize: '0.875rem' } }}
          />
          <IconButton
            type="submit"
            size="small"
            color="primary"
            disabled={!newText.trim() || adding}
          >
            <AddIcon />
          </IconButton>
        </Box>

        {/* Open items */}
        {openItems.length > 0 && (
          <List dense disablePadding>
            {openItems.map((item) => (
              <ListItem
                key={item.id}
                disablePadding
                sx={{ pl: 0, '&:hover .delete-btn': { opacity: 1 } }}
                secondaryAction={
                  <Stack direction="row" spacing={0} alignItems="center">
                    <Tooltip title="Set priority">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          setPriorityAnchor(e.currentTarget);
                          setEditingPriorityId(item.id);
                        }}
                      >
                        <FlagIcon
                          fontSize="small"
                          color={PRIORITY_CONFIG[item.priority]?.color || 'action'}
                        />
                      </IconButton>
                    </Tooltip>
                    <IconButton
                      size="small"
                      className="delete-btn"
                      sx={{ opacity: 0, transition: 'opacity 0.2s' }}
                      onClick={() => handleDelete(item.id)}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Stack>
                }
              >
                <ListItemIcon sx={{ minWidth: 32 }}>
                  <Checkbox
                    edge="start"
                    size="small"
                    checked={false}
                    icon={<UncheckedIcon fontSize="small" />}
                    onChange={() => handleToggle(item)}
                  />
                </ListItemIcon>
                <ListItemText
                  primary={item.text}
                  primaryTypographyProps={{
                    variant: 'body2',
                    sx: { lineHeight: 1.4 },
                  }}
                />
              </ListItem>
            ))}
          </List>
        )}

        {/* Completed items */}
        {doneItems.length > 0 && (
          <>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, mb: 0.5 }}>
              Completed ({doneItems.length})
            </Typography>
            <List dense disablePadding>
              {doneItems.map((item) => (
                <ListItem
                  key={item.id}
                  disablePadding
                  sx={{ pl: 0, opacity: 0.6, '&:hover .delete-btn': { opacity: 1 } }}
                  secondaryAction={
                    <IconButton
                      size="small"
                      className="delete-btn"
                      sx={{ opacity: 0, transition: 'opacity 0.2s' }}
                      onClick={() => handleDelete(item.id)}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  }
                >
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    <Checkbox
                      edge="start"
                      size="small"
                      checked
                      icon={<CheckCircleOutlineIcon fontSize="small" />}
                      onChange={() => handleToggle(item)}
                    />
                  </ListItemIcon>
                  <ListItemText
                    primary={item.text}
                    primaryTypographyProps={{
                      variant: 'body2',
                      sx: { textDecoration: 'line-through', lineHeight: 1.4 },
                    }}
                  />
                </ListItem>
              ))}
            </List>
          </>
        )}

        {total === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1, fontStyle: 'italic' }}>
            No action items yet. Add one above.
          </Typography>
        )}
      </Collapse>

      {/* Priority menu */}
      <Menu
        anchorEl={priorityAnchor}
        open={Boolean(priorityAnchor)}
        onClose={() => { setPriorityAnchor(null); setEditingPriorityId(null); }}
      >
        {Object.entries(PRIORITY_CONFIG).map(([key, config]) => (
          <MenuItem
            key={key}
            onClick={() => handlePriorityChange(editingPriorityId, key)}
          >
            <FlagIcon fontSize="small" color={config.color} sx={{ mr: 1 }} />
            {config.label}
          </MenuItem>
        ))}
      </Menu>
    </Paper>
  );
}
