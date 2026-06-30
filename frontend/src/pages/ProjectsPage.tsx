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
  const [deleteOpened, { open: openDelete, close: closeDelete }] = useDisclosure(false);
  const [projectToDelete, setProjectToDelete] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [path, setPath] = useState('');
  const [description, setDescription] = useState('');
  const navigate = useNavigate();

  const handleCreate = () => {
    createProject.mutate({ name, path: path.trim() || undefined, description }, { onSuccess: close });
  };

  const handleDeleteClick = (id: string) => {
    setProjectToDelete(id);
    openDelete();
  };

  const handleDeleteConfirm = () => {
    if (projectToDelete) {
      deleteProject.mutate(projectToDelete, { onSuccess: closeDelete });
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
                    onClick={(e: React.MouseEvent) => { e.stopPropagation(); handleDeleteClick(p.id); }}
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
          <TextInput label="Project Path (optional)" value={path} onChange={(e) => setPath(e.currentTarget.value)} placeholder="/home/user/projects/my-design" />
          <Textarea label="Description" value={description} onChange={(e) => setDescription(e.currentTarget.value)} />
          <Group justify="flex-end">
            <Button variant="default" onClick={close}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!name.trim()}>Create</Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={deleteOpened} onClose={closeDelete} title="Delete Project" withCloseButton={false}>
        <Stack gap="md">
          <Text>Are you sure you want to delete this project and all its experiments? This action cannot be undone.</Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={closeDelete}>Cancel</Button>
            <Button color="red" onClick={handleDeleteConfirm} loading={deleteProject.isPending}>Delete</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
