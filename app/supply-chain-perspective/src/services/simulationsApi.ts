import type { SimulationRecord } from '../types/simulations';
import { apiGet, apiPost } from './apiClient';

export async function listSimulations(): Promise<SimulationRecord[]> {
  const data = await apiGet<{ simulations: SimulationRecord[] }>('/api/v1/simulations');
  return data.simulations ?? [];
}

export async function createSimulation(payload: {
  name: string;
  description: string;
}): Promise<SimulationRecord> {
  const data = await apiPost<{ simulation: SimulationRecord }>('/api/v1/simulations', payload);
  if (!data.simulation) {
    throw new Error('Invalid response');
  }
  return data.simulation;
}
