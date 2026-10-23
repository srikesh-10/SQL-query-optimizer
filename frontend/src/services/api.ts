import type { AnalyzeQueryResponse, ReadinessResponse } from '../types/analysis';
import type { BenchmarkResponse, BenchmarkListResponse } from '../types/benchmark';
import type { CompareResultsResponse } from '../types/equivalence';
import type { EvaluationResponse, EvaluationListResponse } from '../types/evaluation';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export async function checkBackendReadiness(): Promise<ReadinessResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/health/ready`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      return {
        status: 'unhealthy',
        database: 'disconnected',
        environment: 'unknown',
        version: '0.0.0',
        detail: data.detail || `HTTP ${res.status}: Database unavailable`,
      };
    }
    return await res.json();
  } catch (err) {
    return {
      status: 'offline',
      database: 'unreachable',
      environment: 'unknown',
      version: '0.0.0',
      detail: err instanceof Error ? err.message : 'Cannot connect to backend server',
    };
  }
}

export async function analyzeQuery(sql: string, signal?: AbortSignal): Promise<AnalyzeQueryResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ sql }),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(499, 'Request was cancelled.');
    }
    throw new ApiError(
      0,
      'Failed to connect to the backend server. Ensure FastAPI is running on ' + API_BASE_URL
    );
  }

  if (!response.ok) {
    let errorDetail = 'Unknown error occurred.';
    try {
      const errData = await response.json();
      if (errData && typeof errData === 'object') {
        errorDetail = errData.detail || JSON.stringify(errData);
      }
    } catch {
      errorDetail = `Server returned HTTP ${response.status} ${response.statusText}`;
    }

    if (response.status === 400) {
      throw new ApiError(400, `SQL Validation Failed: ${errorDetail}`);
    } else if (response.status === 422) {
      throw new ApiError(422, `Invalid Request Payload: ${errorDetail}`);
    } else if (response.status === 503) {
      throw new ApiError(503, `Database Service Unavailable: ${errorDetail}`);
    } else if (response.status === 504) {
      throw new ApiError(504, `Query Plan Timeout: ${errorDetail}`);
    } else {
      throw new ApiError(response.status, `Server Error (${response.status}): ${errorDetail}`);
    }
  }

  return response.json();
}

export async function createBenchmark(
  sql: string,
  repetitions: number = 1,
  signal?: AbortSignal
): Promise<BenchmarkResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/benchmarks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ sql, repetitions }),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(499, 'Benchmark request was cancelled.');
    }
    throw new ApiError(
      0,
      'Failed to connect to backend server for benchmarking. Ensure FastAPI is running on ' + API_BASE_URL
    );
  }

  if (!response.ok) {
    let errorDetail = 'Unknown error occurred.';
    try {
      const errData = await response.json();
      if (errData && typeof errData === 'object') {
        errorDetail = errData.detail || JSON.stringify(errData);
      }
    } catch {
      errorDetail = `Server returned HTTP ${response.status} ${response.statusText}`;
    }

    if (response.status === 400) {
      throw new ApiError(400, `Benchmark Safety Rejection: ${errorDetail}`);
    } else if (response.status === 503) {
      throw new ApiError(503, `Database Unavailable: ${errorDetail}`);
    } else {
      throw new ApiError(response.status, `Benchmark Error (${response.status}): ${errorDetail}`);
    }
  }

  return response.json();
}

export async function getBenchmarkHistory(
  limit: number = 20,
  offset: number = 0
): Promise<BenchmarkListResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/benchmarks?limit=${limit}&offset=${offset}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new ApiError(res.status, data.detail || 'Failed to fetch benchmark history.');
    }
    return await res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, err instanceof Error ? err.message : 'Cannot load benchmark history.');
  }
}

export async function getBenchmarkById(id: string): Promise<BenchmarkResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/benchmarks/${encodeURIComponent(id)}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new ApiError(res.status, data.detail || 'Benchmark record not found.');
    }
    return await res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, err instanceof Error ? err.message : 'Failed to retrieve benchmark.');
  }
}

export async function compareResults(
  originalSql: string,
  candidateSql: string,
  confirmed: boolean,
  rowLimit: number = 1000,
  signal?: AbortSignal
): Promise<CompareResultsResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/validation/compare-results`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        original_sql: originalSql,
        candidate_sql: candidateSql,
        confirmed,
        row_limit: rowLimit,
      }),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(499, 'Validation request was cancelled.');
    }
    throw new ApiError(
      0,
      'Failed to connect to backend server for validation. Ensure FastAPI is running on ' + API_BASE_URL
    );
  }

  if (!response.ok) {
    let errorDetail = 'Unknown error occurred.';
    try {
      const errData = await response.json();
      if (errData && typeof errData === 'object') {
        errorDetail = errData.detail || JSON.stringify(errData);
      }
    } catch {
      errorDetail = `Server returned HTTP ${response.status} ${response.statusText}`;
    }

    if (response.status === 400) {
      throw new ApiError(400, `Validation Rejected: ${errorDetail}`);
    } else if (response.status === 503) {
      throw new ApiError(503, `Database Unavailable: ${errorDetail}`);
    } else if (response.status === 504) {
      throw new ApiError(504, `Validation Timeout: ${errorDetail}`);
    } else {
      throw new ApiError(response.status, `Validation Error (${response.status}): ${errorDetail}`);
    }
  }

  return response.json();
}

export async function createEvaluation(
  originalSql: string,
  candidateSql: string,
  confirmed: boolean,
  repetitions: number = 3,
  rowLimit: number = 1000,
  signal?: AbortSignal
): Promise<EvaluationResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/evaluations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        original_sql: originalSql,
        candidate_sql: candidateSql,
        confirmed,
        repetitions,
        row_limit: rowLimit,
      }),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(499, 'Evaluation request was cancelled.');
    }
    throw new ApiError(
      0,
      'Failed to connect to backend server for evaluation. Ensure FastAPI is running on ' + API_BASE_URL
    );
  }

  if (!response.ok) {
    let errorDetail = 'Unknown error occurred.';
    try {
      const errData = await response.json();
      if (errData && typeof errData === 'object') {
        errorDetail = errData.detail || JSON.stringify(errData);
      }
    } catch {
      errorDetail = `Server returned HTTP ${response.status} ${response.statusText}`;
    }

    if (response.status === 400) {
      throw new ApiError(400, `Evaluation Rejected: ${errorDetail}`);
    } else if (response.status === 422) {
      throw new ApiError(422, `Invalid Parameters: ${errorDetail}`);
    } else if (response.status === 503) {
      throw new ApiError(503, `Database Unavailable: ${errorDetail}`);
    } else {
      throw new ApiError(response.status, `Evaluation Error (${response.status}): ${errorDetail}`);
    }
  }

  return response.json();
}

export async function getEvaluationHistory(
  limit: number = 20,
  offset: number = 0
): Promise<EvaluationListResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/evaluations?limit=${limit}&offset=${offset}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new ApiError(res.status, data.detail || 'Failed to fetch evaluation history.');
    }
    return await res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, err instanceof Error ? err.message : 'Cannot load evaluation history.');
  }
}

export async function getEvaluationById(id: string): Promise<EvaluationResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/evaluations/${encodeURIComponent(id)}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new ApiError(res.status, data.detail || 'Evaluation record not found.');
    }
    return await res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, err instanceof Error ? err.message : 'Failed to retrieve evaluation.');
  }
}

