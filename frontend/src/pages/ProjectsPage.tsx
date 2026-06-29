import { useState } from 'react';
import {
  Container,
  Title,
  Table,
  Button,
  Modal,
  TextInput,
  Textarea,
  Group,
  ActionIcon,
  Text,
  Stack,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { useProjects, useCreateProject, useDeleteProject } from '../api/projects';
import type { Project } from '../types';
import { useNavigate } from 'react-router-dom';

export function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();
  const [opened, { open, close }] = useDisclosure(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const navigate = useNavigate();

  const handleCreate = () => {
    createProject.mutate({ name, description }, { onSuccess: close });
  };

  const handleDelete = (id: string) => {
    if (confirm('Delete this project and all its experiments?')) {
      deleteProject.mutate(id);
    }
  };

  return (
    <Container fluid>
      <Group justify="space-between" mb="lg">
        <Title order={2}>Projects</Title>
        <Button leftSection={<IconPlus size={16} />} onClick={open}>
          New Project
        </Button>
      </Group>

      {isLoading && <Text>Loading...</Text>}

      {projects && projects.length > 0 && (
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Path</Table.Th>
              <Table.Th>Experiments</Table.Th>
              <Table.Th>Created</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {projects.map((p: Project) => (
              <Table.Tr
                key={p.id}
                style={{ cursor: 'pointer' }}
                onClick={() => navigate(`/experiments?project_id=${p.id}`)}
              >
                <Table.Td>{p.name}</Table.Td>
                <Table.Td>{p.path || '-'}</Table.Td>
                <Table.Td>{p.experiment_count}</Table.Td>
                <Table.Td>{new Date(p.created_at).toLocaleDateString()}</Table.Td>
                <Table.Td>
                  <ActionIcon
                    color="red"
                    variant="subtle"
                    onClick={(e: React.MouseEvent) => { e.stopPropagation(); handleDelete(p.id); }}
                  >
                    <IconTrash size={16} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {projects && projects.length === 0 && (
        <Text c="dimmed" ta="center" mt="xl">
          No projects yet. Create one to get started.
        </Text>
      )}

      <Modal opened={opened} onClose={close} title="Create Project">
        <Stack gap="md">
          <TextInput label="Project Name" value={name} onChange={(e) => setName(e.currentTarget.value)} required />
          <Textarea label="Description" value={description} onChange={(e) => setDescription(e.currentTarget.value)} />
          <Group justify="flex-end">
            <Button variant="default" onClick={close}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!name.trim()}>Create</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
