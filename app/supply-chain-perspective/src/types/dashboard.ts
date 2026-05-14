/** LlamaStack vector store summary from ``GET /api/v1/vector-stores``. */
export interface VectorStoreSummary {
  id: string;
  name: string;
  status?: string;
  created_at?: number;
}

export type MapViewId = 'airFreight' | 'global' | 'regional';

export type ChatRole = 'human' | 'ai';

/** JSON-serialized OpenAI-style chat completion from the backend (includes ``usage``). */
export type ChatCompletionPayload = Record<string, unknown>;

export interface ChatMessage {
  role: ChatRole;
  content: string;
  /** Present when the last assistant turn came from the LLM stack (tokens, model, etc.). */
  completion?: ChatCompletionPayload | null;
}

/** Body shape for ``POST /api/v1/chat`` success responses. */
export interface ChatApiResponse {
  answer?: string;
  completion?: ChatCompletionPayload | null;
  routeData?: unknown;
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
  /** Live ADS-B style aircraft from OpenSky; drives plane icon in map UIs. */
  is_live?: boolean;
  /** Degrees; used to rotate plane / ship / truck marker. */
  track?: number;
  altitude_ft?: number;
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
