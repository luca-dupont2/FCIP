import { useQuery } from '@tanstack/react-query';
import client from './client';
import type { Report } from '../types';

export function useReports(experimentId?: string, reportType?: string) {
  return useQuery({
    queryKey: ['reports', experimentId, reportType],
    queryFn: async () => {
      const { data } = await client.get('/reports', {
        params: { experiment_id: experimentId, report_type: reportType },
      });
      return data as Report[];
    },
    enabled: !!experimentId,
  });
}

export function useReport(id: string) {
  return useQuery({
    queryKey: ['report', id],
    queryFn: async () => {
      const { data } = await client.get(`/reports/${id}`);
      return data as Report;
    },
    enabled: !!id,
  });
}
