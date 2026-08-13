export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

export type UserRole = 'admin' | 'viewer';

export interface CurrentUser {
  id: string;
  username: string;
  role: UserRole;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'Bearer';
}

export interface CreateUserRequest {
  username: string;
  password: string;
  role: UserRole;
}

export interface UserResponse extends CurrentUser {
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login: string | null;
}

export interface DashboardSummary {
  total_monitors: number;
  active_monitors: number;
  inactive_monitors: number;
  monitors_up: number;
  monitors_down: number;
  monitors_unknown: number;
  slow_monitors: number;
  open_incidents: number;
  average_response_time_ms: number;
  overall_uptime_percentage: number;
}

export interface AuthProfileOption {
  id: string;
  name: string;
}

export interface DashboardIncident {
  id: string;
  monitor_id: string;
  monitor_name: string;
  started_at: string;
  resolved_at: string | null;
  duration_seconds: number | null;
}

export interface DashboardActivity {
  monitor_name: string;
  status: 'up' | 'down' | 'unknown';
  status_code: number | null;
  response_time_ms: number | null;
  is_slow: boolean;
  checked_at: string;
}

export interface ResourceRecord {
  id: string;
  name: string;
  status?: string;
  is_active?: boolean;
  url?: string;
  host?: string;
  login_url?: string;
  method?: string;
  expected_heartbeat_interval?: number;
  last_checked_at?: string | null;
  last_heartbeat_at?: string | null;
  created_at?: string;
}

export interface MonitorOverview {
  id: string;
  name: string;
  monitor_type: string;
  status: 'up' | 'down' | 'unknown';
  is_active: boolean;
  created_at: string;
  last_checked_at: string | null;
  uptime_percentage: number | null;
  current_uptime_seconds: number;
  latest_downtime_seconds: number;
}

export interface MonitorIncident {
  id: string;
  status: 'open' | 'resolved';
  reason: string;
  started_at: string;
  resolved_at: string | null;
  duration_seconds: number;
}

export interface MonitorDetail extends MonitorOverview {
  incidents: MonitorIncident[];
}

export interface StatusHistoryPoint {
  checked_at: string;
  status: 'up' | 'down' | 'unknown';
}

export interface StatusHistory {
  monitor_id: string;
  history: StatusHistoryPoint[];
}

export interface ResponseHistoryPoint {
  checked_at: string;
  response_time_ms: number | null;
}

export interface ResponseHistory {
  monitor_id: string;
  points: ResponseHistoryPoint[];
}

export interface ApiErrorBody {
  message?: string;
  detail?: string | Array<{ msg?: string }>;
}
