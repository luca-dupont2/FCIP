import { Text } from '@mantine/core';

interface DeltaIndicatorProps {
  delta: number | null | undefined;
  invert?: boolean;
}

export function DeltaIndicator({ delta, invert = false }: DeltaIndicatorProps) {
  if (delta == null) return <Text c="dimmed">N/A</Text>;

  const isPositive = invert ? delta < 0 : delta > 0;
  const color = isPositive ? 'green' : delta === 0 ? 'gray' : 'red';
  const sign = delta > 0 ? '+' : '';

  return (
    <Text c={color} fw={500} size="sm">
      {sign}{typeof delta === 'number' ? delta.toFixed(3) : delta}
    </Text>
  );
}
