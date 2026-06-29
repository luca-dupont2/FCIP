import { useState } from 'react';
import { Container, Title, Select, Table, Text, Group } from '@mantine/core';
import { useExperiments } from '../api/experiments';
import { useCompare } from '../api/predictions';
import { DeltaIndicator } from '../components/common/DeltaIndicator';
import { formatDuration } from '../utils/formatters';
import type { MetricDelta, OptionDiff, CompareResult } from '../types';

export function ComparePage() {
  const [expA, setExpA] = useState<string | null>(null);
  const [expB, setExpB] = useState<string | null>(null);
  const compare = useCompare();

  const { data: experimentsData } = useExperiments({ limit: 100 });
  const experiments = experimentsData?.items || [];
  const options = experiments.map((e) => ({ value: e.id, label: e.name || e.id.slice(0, 8) }));

  const handleCompare = () => {
    if (expA && expB && expA !== expB) {
      compare.mutate([expA, expB]);
    }
  };

  const result: CompareResult | undefined = compare.data;

  const fmtVal = (name: string, val: number | undefined | null): string => {
    if (val == null) return 'N/A';
    return name.includes('runtime') ? formatDuration(val) : val.toFixed(3);
  };

  return (
    <Container fluid>
      <Title order={2} mb="lg">Compare Experiments</Title>

      <Group mb="lg">
        <Select
          label="Experiment A"
          placeholder="Select first experiment"
          data={options}
          value={expA}
          onChange={setExpA}
          searchable
          w={300}
        />
        <Select
          label="Experiment B"
          placeholder="Select second experiment"
          data={options}
          value={expB}
          onChange={setExpB}
          searchable
          w={300}
        />
        <Text
          component="button"
          mt="xl"
          disabled={!expA || !expB || expA === expB}
          onClick={handleCompare}
          style={{
            padding: '8px 16px',
            background: (!expA || !expB || expA === expB) ? '#eee' : '#228be6',
            color: (!expA || !expB || expA === expB) ? '#999' : 'white',
            border: 'none',
            borderRadius: 4,
            cursor: (!expA || !expB || expA === expB) ? 'default' : 'pointer',
          }}
        >
          Compare
        </Text>
      </Group>

      {result && (
        <>
          <Title order={4} mb="sm">Metric Comparison</Title>
          <Table striped mb="lg">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Metric</Table.Th>
                <Table.Th>Run A</Table.Th>
                <Table.Th>Run B</Table.Th>
                <Table.Th>Delta</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {Object.entries(result.deltas).map(([name, d]: [string, MetricDelta]) => (
                <Table.Tr key={name}>
                  <Table.Td fw={500}>{name}</Table.Td>
                  <Table.Td>{fmtVal(name, d.a)}</Table.Td>
                  <Table.Td>{fmtVal(name, d.b)}</Table.Td>
                  <Table.Td><DeltaIndicator delta={d.delta} invert={name === 'wns' || name === 'tns' || name === 'total_runtime'} /></Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>

          {Object.keys(result.option_diffs).length > 0 && (
            <>
              <Title order={4} mb="sm">Option Differences</Title>
              <Table striped>
                <Table.Thead>
                  <Table.Tr><Table.Th>Option</Table.Th><Table.Th>Run A</Table.Th><Table.Th>Run B</Table.Th></Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {Object.entries(result.option_diffs).map(([key, vals]: [string, OptionDiff]) => (
                    <Table.Tr key={key}>
                      <Table.Td fw={500}>{key}</Table.Td>
                      <Table.Td>{String(vals.a)}</Table.Td>
                      <Table.Td>{String(vals.b)}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </>
          )}
        </>
      )}
    </Container>
  );
}
