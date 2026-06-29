import { NavLink, Stack, Title, Text } from '@mantine/core';
import {
  IconHome,
  IconFlask,
  IconArrowsExchange,
  IconChartLine,
  IconBulb,
  IconSettings,
} from '@tabler/icons-react';
import { useLocation, useNavigate } from 'react-router-dom';

const links = [
  { label: 'Projects', path: '/', icon: IconHome },
  { label: 'Experiments', path: '/experiments', icon: IconFlask },
  { label: 'Compare', path: '/compare', icon: IconArrowsExchange },
  { label: 'Predictions', path: '/predictions', icon: IconChartLine },
  { label: 'Recommendations', path: '/recommendations', icon: IconBulb },
  { label: 'Settings', path: '/settings', icon: IconSettings },
];

export function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <Stack p="md" gap="xs">
      <Title order={3} mb="md">FCIP</Title>
      <Text size="xs" c="dimmed" mb="sm">FPGA Compile Intelligence</Text>
      {links.map((link) => (
        <NavLink
          key={link.path}
          label={link.label}
          leftSection={<link.icon size={18} />}
          active={location.pathname === link.path || (link.path === '/' && location.pathname === '')}
          onClick={() => navigate(link.path)}
        />
      ))}
    </Stack>
  );
}
