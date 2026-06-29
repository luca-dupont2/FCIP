import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from './client';
import type { Project } from '../types';

export function useProjects(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['projects', limit, offset],
    queryFn: async () => {
      const { data } = await client.get('/projects', { params: { limit, offset } });
      return data as Project[];
    },
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ['project', id],
    queryFn: async () => {
      const { data } = await client.get(`/projects/${id}`);
      return data as Project;
    },
    enabled: !!id,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { name: string; path?: string; description?: string }) => {
      const { data } = await client.post('/projects', body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await client.delete(`/projects/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  });
}
