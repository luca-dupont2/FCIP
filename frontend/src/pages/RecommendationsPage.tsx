import { useState } from 'react';
import { Container, Title, Text, Table, Group, Badge, Progress, Stack, TextInput, Button } from '@mantine/core';
import { useRecommend } from '../api/recommendations';
import type { Recommendation } from '../types';

const categoryColors: Record<string, string> = {
  timing: 'red',
  utilization: 'orange',
  runtime: 'blue',
  strategy: 'violet',
};

export function RecommendationsPage() {
  const [experimentId, setExperimentId] = useState('');
  const recommend = useRecommend();

  const recommendations: Recommendation[] = recommend.data || [];

  return (
    <Container fluid>
      <Title order={2} mb="lg">Recommendations</Title>

      <Stack mb="lg" gap="sm">
        <Text size="sm" c="dimmed">Enter an experiment ID to generate recommendations.</Text>
        <Group>
          <TextInput
            placeholder="Experiment ID"
            value={experimentId}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setExperimentId(e.currentTarget.value)}
            w={300}
          />
          <Button
            onClick={() => recommend.mutate(experimentId)}
            disabled={!experimentId.trim() || recommend.isPending}
            loading={recommend.isPending}
          >
            Get Recommendations
          </Button>
        </Group>
      </Stack>

      {recommendations.length > 0 && (
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Rule</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Priority</Table.Th>
              <Table.Th>Confidence</Table.Th>
              <Table.Th>Message</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {recommendations.map((rec: Recommendation) => (
              <Table.Tr key={rec.rule_name}>
                <Table.Td fw={500}>{rec.rule_name}</Table.Td>
                <Table.Td>
                  <Badge color={categoryColors[rec.category] || 'gray'} variant="light">
                    {rec.category}
                  </Badge>
                </Table.Td>
                <Table.Td>{rec.priority || '-'}</Table.Td>
                <Table.Td>
                  {rec.confidence != null ? (
                    <Group gap="xs">
                      <Progress value={rec.confidence * 100} size="sm" w={60} />
                      <Text size="sm">{(rec.confidence * 100).toFixed(0)}%</Text>
                    </Group>
                  ) : '-'}
                </Table.Td>
                <Table.Td>{rec.message}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {!recommend.isPending && recommendations.length === 0 && experimentId && (
        <Text c="dimmed" ta="center" mt="xl">No recommendations for this experiment.</Text>
      )}
    </Container>
  );
}
