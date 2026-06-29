import { useMutation } from '@tanstack/react-query';
import client from './client';
import type { Recommendation } from '../types';

export function useRecommend() {
  return useMutation({
    mutationFn: async (experimentId: string) => {
      const { data } = await client.post('/recommend', { experiment_id: experimentId });
      return data as Recommendation[];
    },
  });
}
