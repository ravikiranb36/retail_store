import { HttpInterceptorFn, HttpErrorResponse, HttpClient, HttpBackend } from '@angular/common/http';
import { inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { catchError, switchMap, throwError } from 'rxjs';
import { Router } from '@angular/router';
import { API_BASE_URL } from '../constants/api.constants';

// Helper to decode JWT and check expiry
function isTokenExpired(token: string | null): boolean {
  if (!token) return true;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    // exp is in seconds
    return Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const platformId = inject(PLATFORM_ID);
  const router = inject(Router);
  const httpBackend = inject(HttpBackend);
  const httpClient = new HttpClient(httpBackend);

  const tokenKey = 'access_token';
  const refreshTokenKey = 'refresh_token';
  let token: string | null = null;
  let refreshToken: string | null = null;

  if (isPlatformBrowser(platformId)) {
    token = localStorage.getItem(tokenKey);
    refreshToken = localStorage.getItem(refreshTokenKey);
  }

  // Do not add token for login or refresh endpoints
  if (req.url.includes('/login/') || req.url.includes('/token/refresh/')) {
    return next(req);
  }

  // Helper to handle logout
  function handleLogout() {
    if (isPlatformBrowser(platformId)) {
      localStorage.removeItem(tokenKey);
      localStorage.removeItem(refreshTokenKey);
    }
    router.navigate(['/login']);
  }

  // Helper to refresh token
  function refreshTokenAndRetry(failedRequest: any) {
      if (!refreshToken) {
          handleLogout();
          return throwError(() => new Error('No refresh token'));
      }

      return httpClient.post<any>(`${API_BASE_URL}token/refresh/`, { refresh: refreshToken }).pipe(
          switchMap((response: any) => {
              const newToken = response.access;
              if (isPlatformBrowser(platformId)) {
                  localStorage.setItem(tokenKey, newToken);
                  if (response.refresh) {
                      localStorage.setItem(refreshTokenKey, response.refresh);
                  }
              }

              // Clone the original request with the new token
              const newReq = failedRequest.clone({
                  setHeaders: {
                      Authorization: `Bearer ${newToken}`
                  }
              });
              return next(newReq);
          }),
          catchError((refreshErr) => {
              handleLogout();
              return throwError(() => refreshErr);
          })
      );
  }

  // Proactively refresh token if expired before sending request
  if (token && isTokenExpired(token) && refreshToken) {
    return refreshTokenAndRetry(req);
  }

  // Attach token if present and not expired
  let authReq = req;
  if (token && !isTokenExpired(token)) {
    authReq = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // On 401, try to refresh token (fallback)
      if (error.status === 401 && refreshToken && !req.url.includes('/login/') && !req.url.includes('/token/refresh/')) {
        return refreshTokenAndRetry(req);
      }
      // Any other error or no refresh token, logout if it's a 401
      if (error.status === 401) {
          handleLogout();
      }
      return throwError(() => error);
    })
  );
};
