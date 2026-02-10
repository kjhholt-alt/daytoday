import React from 'react';
import { Chip } from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  HourglassEmpty as PendingIcon,
  Sync as CollectingIcon,
} from '@mui/icons-material';

const statusConfig = {
  complete: { color: 'success', icon: <CheckIcon />, label: 'Complete' },
  error: { color: 'error', icon: <ErrorIcon />, label: 'Error' },
  pending: { color: 'default', icon: <PendingIcon />, label: 'Pending' },
  collecting: { color: 'info', icon: <CollectingIcon />, label: 'Collecting' },
};

export default function StatusBadge({ status }) {
  const config = statusConfig[status] || statusConfig.pending;
  return (
    <Chip
      icon={config.icon}
      label={config.label}
      color={config.color}
      size="small"
      variant="outlined"
    />
  );
}
