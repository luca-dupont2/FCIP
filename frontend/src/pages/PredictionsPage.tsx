import { useState } from 'react';
import { Container, Title, Text, Group, Stack, Card, SimpleGrid, RingProgress, NumberInput, Select, Switch, Button, TextInput } from '@mantine/core';
import { usePredict } from '../api/predictions';
import { formatDuration } from '../utils/formatters';

export function PredictionsPage() {
  const predict = usePredict();
  const [experimentId, setExperimentId] = useState('');
  const [device, setDevice] = useState('');
  const [lutPct, setLutPct] = useState<number | ''>('');
  const [ffPct, setFfPct] = useState<number | ''>('');
  const [bramPct, setBramPct] = useState<number | ''>('');
  const [dspPct, setDspPct] = useState<number | ''>('');
  const [seed, setSeed] = useState<number | ''>('');
  const [retiming, setRetiming] = useState(false);
  const [physOpt, setPhysOpt] = useState(false);

  const handlePredict = () => {
    const body: Record<string, unknown> = {
      device: device || 'unknown',
      lut_pct: lutPct || undefined,
      ff_pct: ffPct || undefined,
      bram_pct: bramPct || undefined,
      dsp_pct: dspPct || undefined,
      seed: seed || undefined,
      retiming,
      phys_opt: physOpt,
    };
    if (experimentId.trim()) {
      body.experiment_id = experimentId.trim();
    }
    predict.mutate(body);
  };

  const result = predict.data;

  return (
    <Container fluid>
      <Title order={2} mb="lg">Predictions</Title>

      <Card withBorder p="lg" mb="lg">
        <Stack gap="md">
          <Text fw={500}>Input Features</Text>
          <Text size="sm" c="dimmed">Enter an existing experiment ID, or fill in the features manually.</Text>
          <TextInput
            label="Experiment ID"
            placeholder="Paste experiment ID (optional)"
            value={experimentId}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setExperimentId(e.currentTarget.value)}
          />
          <SimpleGrid cols={3}>
            <Select
              label="Device"
              data={[
                'xcvu9p-flgb2104-2-e',
                'xcvu3p-ffvc1517-2-e',
                'xcku060-ffva1156-2-e',
                '5CEFA7F31C6',
                '10AS066N3F40E2SG',
              ]}
              value={device}
              onChange={(v: string | null) => setDevice(v || '')}
              searchable
            />
            <NumberInput label="LUT %" value={lutPct} onChange={(v) => setLutPct(v as number | '')} min={0} max={100} />
            <NumberInput label="FF %" value={ffPct} onChange={(v) => setFfPct(v as number | '')} min={0} max={100} />
            <NumberInput label="BRAM %" value={bramPct} onChange={(v) => setBramPct(v as number | '')} min={0} max={100} />
            <NumberInput label="DSP %" value={dspPct} onChange={(v) => setDspPct(v as number | '')} min={0} max={100} />
            <NumberInput label="Seed" value={seed} onChange={(v) => setSeed(v as number | '')} min={1} max={100} />
          </SimpleGrid>
          <Group>
            <Switch label="Retiming" checked={retiming} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRetiming(e.currentTarget.checked)} />
            <Switch label="Physical Optimization" checked={physOpt} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPhysOpt(e.currentTarget.checked)} />
          </Group>
          <Button onClick={handlePredict} loading={predict.isPending}>Predict</Button>
        </Stack>
      </Card>

      {result && (
        <SimpleGrid cols={3}>
          <Card withBorder p="lg">
            <Text ta="center" size="sm" c="dimmed">Expected WNS</Text>
            <Text ta="center" fw={700} size="xl">
              {result.expected_wns != null ? `${result.expected_wns.toFixed(3)} ns` : 'N/A'}
            </Text>
          </Card>
          <Card withBorder p="lg">
            <Text ta="center" size="sm" c="dimmed">Expected Duration</Text>
            <Text ta="center" fw={700} size="xl">
              {result.expected_compile_duration != null ? formatDuration(result.expected_compile_duration) : 'N/A'}
            </Text>
          </Card>
          <Card withBorder p="lg">
            <Text ta="center" size="sm" c="dimmed">Timing Success</Text>
            {result.timing_success_probability != null ? (
              <RingProgress
                sections={[{ value: result.timing_success_probability * 100, color: 'green' }]}
                label={<Text ta="center" fw={700}>{(result.timing_success_probability * 100).toFixed(0)}%</Text>}
                size={120}
              />
            ) : <Text ta="center">N/A</Text>}
          </Card>
        </SimpleGrid>
      )}

      {result?.error && <Text c="red" mt="md">{result.error}</Text>}
    </Container>
  );
}
