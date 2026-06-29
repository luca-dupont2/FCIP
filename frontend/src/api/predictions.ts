import { useMutation, useQuery } from '@tanstack/react-query';
import client from './client';
import type { Prediction, CompareResult } from '../types';

export function usePredict() {
  return useMutation({
    mutationFn: async (body: Record<string, unknown>) => {
      const { data } = await client.post('/predict', body);
      return data as Prediction;
    },
  });
}

export function useCompare() {
  return useMutation({
    mutationFn: async (experimentIds: string[]) => {
      const { data } = await client.post('/compare', { experiment_ids: experimentIds });
      return data as CompareResult;
    },
  });
}

export function useTrainModels() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await client.post('/predict/train');
      return data;
    },
  });
}

export function useModels() {
  return useQuery({
    queryKey: ['models'],
    queryFn: async () => {
      const { data } = await client.get('/predict/models');
      return data;
    },
    refetchInterval: 30000,
  });
}
