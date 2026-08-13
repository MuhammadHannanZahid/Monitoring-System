import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiErrorBody, ApiResponse } from './models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/api';
  private readonly options = { withCredentials: true };

  get<T>(path: string): Observable<ApiResponse<T>> {
    return this.http.get<ApiResponse<T>>(`${this.baseUrl}${path}`, this.options);
  }

  post<T, B = unknown>(path: string, body: B): Observable<ApiResponse<T>> {
    return this.http.post<ApiResponse<T>>(`${this.baseUrl}${path}`, body, this.options);
  }

  put<T, B = unknown>(path: string, body: B): Observable<ApiResponse<T>> {
    return this.http.put<ApiResponse<T>>(`${this.baseUrl}${path}`, body, this.options);
  }

  delete<T>(path: string): Observable<ApiResponse<T>> {
    return this.http.delete<ApiResponse<T>>(`${this.baseUrl}${path}`, this.options);
  }

  static errorMessage(error: unknown): string {
    if (!(error instanceof HttpErrorResponse)) {
      return 'Something went wrong. Please try again.';
    }

    const body = error.error as ApiErrorBody | string | null;
    if (typeof body === 'string' && body.trim()) {
      return body;
    }
    if (body && typeof body === 'object') {
      if (body.message) {
        return body.message;
      }
      if (typeof body.detail === 'string') {
        return body.detail;
      }
      if (Array.isArray(body.detail)) {
        return body.detail
          .map((item) => item.msg)
          .filter(Boolean)
          .join(' ');
      }
    }
    return error.status === 0
      ? 'The backend is unavailable. Check that it is running on port 8000.'
      : `Request failed with status ${error.status}.`;
  }
}
