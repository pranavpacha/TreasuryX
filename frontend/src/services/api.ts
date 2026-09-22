import axios from "axios";

// In local dev, Vite proxies "/api" to the backend (see vite.config.ts).
// In production, set VITE_API_BASE_URL to the deployed backend's full URL, e.g.
// https://treasuryx-backend.onrender.com/api
const baseURL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "/api";

export const api = axios.create({ baseURL });

export interface FxQuote {
  pair: string;
  rate: number;
  bid: number;
  ask: number;
  spread: number;
  day_return_pct: number;
  annualized_vol_pct: number;
  date: string;
  source: string;
  is_demo: boolean;
  is_cv_corrected?: boolean;
}

export interface FxHistoryPoint {
  date: string;
  rate: number;
  bid: number;
  ask: number;
}

export interface FxPositionView {
  pair: string;
  notional_base: number;
  entry_rate: number;
  current_rate: number;
  pnl_inr: number;
  return_pct: number;
}

export interface Bond {
  isin: string;
  name: string;
  coupon_rate_pct: number;
  maturity_date: string;
  years_to_maturity: number;
  current_yield_pct: number;
  clean_price: number;
  modified_duration: number;
  macaulay_duration: number;
  convexity: number;
  dv01_per_100_face: number;
  is_cv_corrected?: boolean;
}

export interface BondPositionView {
  isin: string;
  name: string;
  quantity_face: number;
  clean_price: number;
  current_yield_pct: number;
  modified_duration: number;
  convexity: number;
  dv01_inr: number;
  market_value_inr: number;
}

export interface YieldPoint {
  tenor: string;
  years: number;
  yield_pct: number;
  date: string;
}

export interface RiskSummary {
  as_of: string;
  fx_exposure_inr: number;
  fx_pnl_inr: number;
  bond_market_value_inr: number;
  bond_dv01_inr_per_bp: number;
  total_pnl_inr: number;
  portfolio_value_inr: number;
  var: {
    var_amount_inr: number; es_amount_inr: number; confidence: number;
    horizon_days: number; lookback_obs: number; method: string;
  } | null;
  var_warning: string | null;
  max_drawdown_inr: number;
  regime: string;
  regime_reasons: string[];
  risk_limits: {
    fx_exposure_limit_inr: number; fx_exposure_utilization_pct: number;
    bond_dv01_limit_inr: number; bond_dv01_utilization_pct: number;
  };
}

export interface Overview {
  as_of: string;
  fx_snapshot: { pair: string; rate: number; is_cv_corrected?: boolean }[];
  curve_snapshot: { tenor: string; yield_pct: number }[];
  selected_bond: { isin: string; name: string; current_yield_pct: number } | null;
  risk: RiskSummary;
  market_events: { headline: string; category: string; severity: string; created_at: string }[];
  is_demo: boolean;
  data_status: {
    mode: string; last_updated: string | null; source: string;
    active_cv_corrections: { instrument_type: string; instrument_id: string; field: string; value: number; applied_at: string }[];
  };
  disclaimer: string;
}

export interface Trade {
  id: number;
  instrument_type: string;
  instrument_id: string;
  side: string;
  quantity: number;
  price: number;
  notional: number;
  trade_type: string;
  status: string;
  created_at: string;
}

export interface ScenarioResponse {
  id: number;
  label: string;
  inputs: Record<string, unknown>;
  fx_pnl_by_pair: Record<string, number>;
  bond_pnl_by_isin: Record<string, number>;
  total_fx_pnl: number;
  total_bond_pnl: number;
  total_pnl: number;
  shocked_fx_rates: Record<string, number>;
  shocked_bond_yields: Record<string, number>;
  method_notes: string[];
}

export interface CvField {
  instrument: string | null; metric: string | null; value: number | null;
  unit: string | null; confidence: number; source_region: number[] | null;
  flagged?: boolean; flag_reason?: string | null;
}

export interface CvModelPrediction {
  label: string;
  confidence: number;
  inference_ms: number;
}

export interface CvModelDetails {
  available: boolean;
  reason?: string;
  classes?: string[];
  cnn?: CvModelPrediction;
  vit?: CvModelPrediction;
  agree?: boolean;
  note?: string;
}

export interface CvImageQuality {
  width: number;
  height: number;
  blur_variance: number;
  contrast_std: number;
  verdict: "low" | "ok";
  reasons: string[];
  recommendation: string | null;
}

export interface CvExtractionResult {
  id: number;
  original_filename: string;
  chart_type: string;
  image_quality: CvImageQuality;
  stages: Record<string, string>;
  ocr_text_raw: string;
  ocr_available: boolean;
  fields: CvField[];
  mean_confidence: number;
  warnings: string[];
  model_details: CvModelDetails;
}

export interface CvCommitResult {
  instrument_id: string;
  field: string;
  previous_value: number;
  new_value: number;
  delta?: number;
  delta_bps?: number;
  clean_price_before?: number;
  clean_price_after?: number;
  modified_duration_after?: number;
  convexity_after?: number;
  dv01_per_100_face_after?: number;
  affected_open_positions: Record<string, unknown>[];
}

export const fetchOverview = () => api.get<Overview>("/overview").then((r) => r.data);
export const fetchFxQuotes = () => api.get<FxQuote[]>("/fx/quotes").then((r) => r.data);
export const fetchFxHistory = (pair: string, lookback = 250) =>
  api.get<FxHistoryPoint[]>(`/fx/history/${pair}`, { params: { lookback_days: lookback } }).then((r) => r.data);
export const fetchFxPositions = () => api.get<FxPositionView[]>("/fx/positions").then((r) => r.data);
export const postFxTrade = (body: { instrument_id: string; side: "BUY" | "SELL"; quantity: number; price: number }) =>
  api.post<Trade>("/fx/trade", { instrument_type: "FX", ...body }).then((r) => r.data);

export const fetchBonds = () => api.get<Bond[]>("/bonds").then((r) => r.data);
export const fetchBondHistory = (isin: string, lookback = 250) =>
  api.get<{ date: string; yield_pct: number; clean_price: number }[]>(`/bonds/${isin}/history`, { params: { lookback_days: lookback } }).then((r) => r.data);
export const fetchBondPositions = () => api.get<BondPositionView[]>("/positions/bonds").then((r) => r.data);
export const postBondTrade = (body: { instrument_id: string; side: "BUY" | "SELL"; quantity: number; price: number }) =>
  api.post<Trade>("/positions/bonds/trade", { instrument_type: "BOND", ...body }).then((r) => r.data);

export const fetchYieldCurve = (asOf?: string) => api.get<YieldPoint[]>("/yield-curve", { params: asOf ? { as_of: asOf } : {} }).then((r) => r.data);
export const fetchYieldCurveDates = () => api.get<string[]>("/yield-curve/dates").then((r) => r.data);
export const fetchYieldCurveCompare = (date1: string, date2: string) =>
  api.get("/yield-curve/compare", { params: { date1, date2 } }).then((r) => r.data);

export const fetchRiskSummary = (confidence = 0.95, lookbackDays = 250) =>
  api.get<RiskSummary>("/risk/summary", { params: { confidence, lookback_days: lookbackDays } }).then((r) => r.data);

export const runScenario = (body: {
  label: string; fx_shock_pct: Record<string, number>; parallel_yield_shock_bps: number;
  curve_tilt_bps: number; per_bond_yield_shock_bps: Record<string, number>;
}) => api.post<ScenarioResponse>("/scenario/run", body).then((r) => r.data);
export const fetchScenarioHistory = () => api.get<ScenarioResponse[]>("/scenario/history").then((r) => r.data);

export const fetchTradeBlotter = () => api.get<Trade[]>("/positions/blotter").then((r) => r.data);

export const uploadCvImage = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post<CvExtractionResult>("/cv/extract", form, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
};
export const correctCvExtraction = (extraction_id: number, corrected_fields: CvField[]) =>
  api.post("/cv/correct", { extraction_id, corrected_fields }).then((r) => r.data);
export const commitCvExtraction = (extraction_id: number, target: string, instrument_id: string) =>
  api.post<CvCommitResult>("/cv/commit", { extraction_id, target, instrument_id }).then((r) => r.data);
export const fetchCvOverrides = () => api.get("/cv/overrides").then((r) => r.data);
export const resetCvOverrides = () => api.delete("/cv/overrides").then((r) => r.data);

export const fetchYieldSurface = (nDates = 30) =>
  api.get<{ dates: string[]; points: { date: string; tenor: string; years: number; yield_pct: number }[] }>(
    "/market3d/yield-surface", { params: { n_dates: nDates } },
  ).then((r) => r.data);
export const fetchFxVolSurface = () =>
  api.get<{ pairs: string[]; windows: number[]; points: { pair: string; window_days: number; annualized_vol_pct: number }[] }>(
    "/market3d/fx-vol-surface",
  ).then((r) => r.data);
export const fetchStressSurface = (fxSteps = 9, yieldSteps = 9) =>
  api.get<{ grid: { fx_shock_pct: number; yield_shock_bps: number; total_pnl_inr: number }[]; has_positions: boolean }>(
    "/market3d/stress-surface", { params: { fx_steps: fxSteps, yield_steps: yieldSteps } },
  ).then((r) => r.data);
