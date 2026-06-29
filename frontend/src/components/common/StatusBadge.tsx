import { Badge } from '@mantine/core';

const statusColors: Record<string, string> = {
  running: 'blue',
  success: 'green',
  failed: 'red',
  timeout: 'orange',
};

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <Badge color={statusColors[status] || 'gray'} variant="light">
      {status}
    </Badge>
  );
}
