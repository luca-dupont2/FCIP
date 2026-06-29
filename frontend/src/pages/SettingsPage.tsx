import { Container, Title, Text, Stack, Card, Group, Button } from '@mantine/core';
import { useTrainModels, useModels } from '../api/predictions';

interface ModelEntry {
  id: string;
  model_type: string;
  version: number;
  accuracy?: number;
  dataset_size?: number;
  trained_at?: string;
  error?: string;
}

export function SettingsPage() {
  const trainModels = useTrainModels();
  const { data: models } = useModels();

  return (
    <Container fluid>
      <Title order={2} mb="lg">Settings</Title>

      <Stack gap="lg">
        <Card withBorder p="lg">
          <Title order={4} mb="sm">ML Models</Title>
          <Text size="sm" c="dimmed" mb="md">
            Retrain prediction models with current experiment data.
          </Text>
          <Button onClick={() => trainModels.mutate()} loading={trainModels.isPending}>
            Retrain Models
          </Button>
          {trainModels.data && (
            <Text size="sm" c="green" mt="sm">Training successful!</Text>
          )}
          {trainModels.data?.error && (
            <Text size="sm" c="red" mt="sm">Error: {trainModels.data.error}</Text>
          )}
        </Card>

        <Card withBorder p="lg">
          <Title order={4} mb="sm">Trained Models</Title>
          {models && models.length > 0 ? (
            <Stack gap="xs">
              {models.map((m: ModelEntry) => (
                <Group key={m.id} justify="space-between">
                  <Text size="sm">{m.model_type} (v{m.version})</Text>
                  <Text size="sm" c="dimmed">
                    Accuracy: {m.accuracy?.toFixed(3) || 'N/A'} | Dataset: {m.dataset_size || 'N/A'} |
                    Trained: {m.trained_at ? new Date(m.trained_at).toLocaleDateString() : 'N/A'}
                  </Text>
                </Group>
              ))}
            </Stack>
          ) : (
            <Text size="sm" c="dimmed">No trained models yet.</Text>
          )}
        </Card>

        <Card withBorder p="lg">
          <Title order={4} mb="sm">About</Title>
          <Text size="sm">FCIP - FPGA Compile Intelligence Platform v0.1.0</Text>
          <Text size="sm" c="dimmed">Local-first FPGA experiment tracking, analysis, and prediction.</Text>
        </Card>
      </Stack>
    </Container>
  );
}
