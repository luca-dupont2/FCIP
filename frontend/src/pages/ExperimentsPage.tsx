import { useState } from 'react';
import {
  Container,
  Title,
  Table,
  Text,
  Select,
  Group,
  Pagination,
} from '@mantine/core';
import { useExperiments } from '../api/experiments';
import { StatusBadge } from '../components/common/StatusBadge';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { Experiment } from '../types';

export function ExperimentsPage() {
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get('project_id') || undefined;
  const [page, setPage] = useState(1);
  const [tool, setTool] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const navigate = useNavigate();

  const { data, isLoading } = useExperiments({
    project_id: projectId,
    tool: tool || undefined,
    status: status || undefined,
    limit: 20,
    offset: (page - 1) * 20,
  });

  const experiments = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 20);

  return (
    <Container fluid>
      <Title order={2} mb="lg">Experiments</Title>

      <Group mb="md">
        <Select
          placeholder="Tool"
          data={[
            { value: 'vivado', label: 'Vivado' },
            { value: 'quartus', label: 'Quartus' },
          ]}
          value={tool}
          onChange={setTool}
          clearable
          w={150}
        />
        <Select
          placeholder="Status"
          data={[
            { value: 'running', label: 'Running' },
            { value: 'success', label: 'Success' },
            { value: 'failed', label: 'Failed' },
            { value: 'timeout', label: 'Timeout' },
          ]}
          value={status}
          onChange={setStatus}
          clearable
          w={150}
        />
      </Group>

      {isLoading && <Text>Loading...</Text>}

      {experiments.length > 0 && (
        <>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Name</Table.Th>
                <Table.Th>Tool</Table.Th>
                <Table.Th>Device</Table.Th>
                <Table.Th>Seed</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Created</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {experiments.map((exp: Experiment) => (
                <Table.Tr
                  key={exp.id}
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/experiments/${exp.id}`)}
                >
                  <Table.Td>{exp.name || exp.id.slice(0, 8)}</Table.Td>
                  <Table.Td>{exp.tool}</Table.Td>
                  <Table.Td>{exp.device || '-'}</Table.Td>
                  <Table.Td>{exp.seed ?? '-'}</Table.Td>
                  <Table.Td><StatusBadge status={exp.status} /></Table.Td>
                  <Table.Td>{new Date(exp.created_at).toLocaleDateString()}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          {totalPages > 1 && (
            <Group justify="center" mt="md">
              <Pagination value={page} onChange={setPage} total={totalPages} />
            </Group>
          )}
        </>
      )}

      {!isLoading && experiments.length === 0 && (
        <Text c="dimmed" ta="center" mt="xl">No experiments found.</Text>
      )}
    </Container>
  );
}
