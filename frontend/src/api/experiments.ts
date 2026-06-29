import { useQuery } from '@tanstack/react-query';
import client from './client';
import type { ExperimentList } from '../types';

export function useExperiments(params: {
  project_id?: string;
  tool?: string;
  status?: string;
  branch?: string;
  seed?: number;
  limit?: number;
  offset?: number;
} = {}) {
  return useQuery({
    queryKey: ['experiments', params],
    queryFn: async () => {
      const { data } = await client.get('/experiments', { params });
      return data as ExperimentList;
    },
  });
}

export function useExperiment(id: string) {
  return useQuery({
    queryKey: ['experiment', id],
    queryFn: async () => {
      const { data } = await client.get(`/experiments/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useSearchExperiments(params: {
  q?: string;
  project_id?: string;
  tool?: string;
  seed?: number;
  branch?: string;
  sort_by?: string;
  limit?: number;
  offset?: number;
} = {}) {
  return useQuery({
    queryKey: ['search', params],
    queryFn: async () => {
      const { data } = await client.get('/experiments/search', { params });
      return data as ExperimentList;
    },
  });
}
