export type MapViewId = 'airFreight' | 'global' | 'regional';

export type ChatRole = 'human' | 'ai';

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface MapPort {
  name: string;
  lat: number;
  lng: number;
  risk?: number;
}

export interface MapAsset {
  id?: string;
  name?: string;
  lat?: number;
  lng?: number;
  cargo?: string;
  speed?: string;
}

export interface MapLayerData {
  ports?: MapPort[];
  assets?: MapAsset[];
}

export interface DashboardAlert {
  type?: string;
  text: string;
}

export interface KpiValue {
  value?: string;
}

export interface DashboardCharts {
  demand?: {
    labels?: string[];
    actual?: number[];
    forecast?: number[];
  };
  revenue?: {
    revenueData?: number[];
    marginData?: number[];
    colors?: string[];
  };
}

/** Populated by `POST /api/v1/simulate` (Flask `dashboard_service.simulate`). */
export interface SimulationPerformance {
  mode?: string;
  cacheRate?: string;
  latency?: string;
  costSavings?: string;
  totalTokens?: string;
  tokensPerSecond?: string;
}

export interface DashboardState {
  kpis?: Record<string, KpiValue>;
  alerts?: {
    global?: DashboardAlert[];
    regional?: DashboardAlert[];
    airFreight?: DashboardAlert[];
  };
  mapData?: Partial<Record<MapViewId, MapLayerData>>;
  charts?: DashboardCharts;
  performance?: SimulationPerformance;
}

export type SystemHealthRiskLevel = 'low' | 'medium' | 'critical';

export interface SystemHealthView {
  supplierHealth: number;
  inventoryHealth: number;
  riskIndex: number;
  riskLevel: SystemHealthRiskLevel;
  dataFreshnessPercent: number;
}
