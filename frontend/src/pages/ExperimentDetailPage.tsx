import { Container, Title, Text, Stack, Group, Tabs, Table, SimpleGrid, Card, Progress } from '@mantine/core';
import { useParams } from 'react-router-dom';
import { useExperiment } from '../api/experiments';
import { useReports } from '../api/reports';
import { StatusBadge } from '../components/common/StatusBadge';
import { formatWns, formatDuration, utilizationColor } from '../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { Report } from '../types';

export function ExperimentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: experiment, isLoading } = useExperiment(id || '');
  const { data: reports } = useReports(id);

  if (isLoading) return <Text>Loading...</Text>;
  if (!experiment) return <Text>Experiment not found.</Text>;

  const timingReport = reports?.find((r: Report) => r.report_type === 'timing');
  const utilReport = reports?.find((r: Report) => r.report_type === 'utilization');
  const runtimeReport = reports?.find((r: Report) => r.report_type === 'runtime');

  const utilData = utilReport
    ? [
        { name: 'LUT', used: utilReport.lut || 0, available: utilReport.lut_available || 0 },
        { name: 'FF', used: utilReport.ff || 0, available: utilReport.ff_available || 0 },
        { name: 'BRAM', used: utilReport.bram || 0, available: utilReport.bram_available || 0 },
        { name: 'DSP', used: utilReport.dsp || 0, available: utilReport.dsp_available || 0 },
      ].map((d) => ({ ...d, pct: d.available > 0 ? (d.used / d.available) * 100 : 0 }))
    : [];

  return (
    <Container fluid>
      <Group justify="space-between" mb="lg">
        <Title order={2}>{experiment.name || 'Experiment'}</Title>
        <StatusBadge status={experiment.status} />
      </Group>

      <SimpleGrid cols={3} mb="lg">
        <Card><Text size="sm" c="dimmed">Tool</Text><Text fw={500}>{experiment.tool}</Text></Card>
        <Card><Text size="sm" c="dimmed">Device</Text><Text fw={500}>{experiment.device || '-'}</Text></Card>
        <Card><Text size="sm" c="dimmed">Seed</Text><Text fw={500}>{experiment.seed ?? '-'}</Text></Card>
        <Card><Text size="sm" c="dimmed">Branch</Text><Text fw={500}>{experiment.branch || '-'}</Text></Card>
        <Card><Text size="sm" c="dimmed">Commit</Text><Text fw={500} style={{fontFamily:'monospace'}}>{experiment.git_commit?.slice(0, 8) || '-'}</Text></Card>
        <Card><Text size="sm" c="dimmed">Created</Text><Text fw={500}>{new Date(experiment.created_at).toLocaleString()}</Text></Card>
      </SimpleGrid>

      <Tabs defaultValue="timing">
        <Tabs.List>
          <Tabs.Tab value="timing">Timing</Tabs.Tab>
          <Tabs.Tab value="utilization">Utilization</Tabs.Tab>
          <Tabs.Tab value="runtime">Runtime</Tabs.Tab>
          <Tabs.Tab value="options">Options</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="timing" pt="md">
          {timingReport ? (
            <Stack gap="sm">
              <Group>
                <Text fw={500}>WNS:</Text>
                <Text c={formatWns(timingReport.wns).color} fw={700}>
                  {formatWns(timingReport.wns).text} ns
                </Text>
              </Group>
              <Group><Text fw={500}>TNS:</Text><Text>{timingReport.tns?.toFixed(3) || 'N/A'} ns</Text></Group>
              <Group><Text fw={500}>Failing Paths:</Text><Text>{timingReport.failing_paths ?? 'N/A'}</Text></Group>
            </Stack>
          ) : (
            <Text c="dimmed">No timing report available.</Text>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="utilization" pt="md">
          {utilReport ? (
            <Stack gap="md">
              <Table>
                <Table.Thead>
                  <Table.Tr><Table.Th>Resource</Table.Th><Table.Th>Used</Table.Th><Table.Th>Available</Table.Th><Table.Th>Utilization</Table.Th></Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {utilData.map((d) => (
                    <Table.Tr key={d.name}>
                      <Table.Td>{d.name}</Table.Td>
                      <Table.Td>{d.used.toLocaleString()}</Table.Td>
                      <Table.Td>{d.available.toLocaleString()}</Table.Td>
                      <Table.Td>
                        <Progress value={d.pct} color={utilizationColor(d.pct / 100)} size="sm" />
                        <Text size="xs" mt={2}>{d.pct.toFixed(1)}%</Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
              <div style={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={utilData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="pct" fill="#228be6" name="Utilization %" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Stack>
          ) : (
            <Text c="dimmed">No utilization report available.</Text>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="runtime" pt="md">
          {runtimeReport ? (
            <Stack gap="sm">
              <Group><Text fw={500}>Synthesis:</Text><Text>{formatDuration(runtimeReport.synthesis_duration)}</Text></Group>
              <Group><Text fw={500}>Implementation:</Text><Text>{formatDuration(runtimeReport.implementation_duration)}</Text></Group>
              <Group><Text fw={500}>Bitstream:</Text><Text>{formatDuration(runtimeReport.bitstream_duration)}</Text></Group>
              <Group><Text fw={500} size="lg">Total:</Text><Text size="lg" fw={700}>{formatDuration(runtimeReport.total_runtime)}</Text></Group>
            </Stack>
          ) : (
            <Text c="dimmed">No runtime report available.</Text>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="options" pt="md">
          {experiment.compile_options && Object.keys(experiment.compile_options).length > 0 ? (
            <Table>
              <Table.Thead>
                <Table.Tr><Table.Th>Option</Table.Th><Table.Th>Value</Table.Th></Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {Object.entries(experiment.compile_options).map(([k, v]) => (
                  <Table.Tr key={k}><Table.Td>{k}</Table.Td><Table.Td>{String(v)}</Table.Td></Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          ) : (
            <Text c="dimmed">No compile options recorded.</Text>
          )}
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}
