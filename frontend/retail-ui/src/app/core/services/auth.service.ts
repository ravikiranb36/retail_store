import { Injectable, signal, computed, PLATFORM_ID, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, of, catchError, switchMap } from 'rxjs';
import { Router } from '@angular/router';
import { isPlatformBrowser } from '@angular/common';
import { API_BASE_URL } from '../constants/api.constants';

export interface User {
  username: string;
  roles: string[];
  token: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private baseUrl = API_BASE_URL;
  private tokenKey = 'access_token';
  private refreshTokenKey = 'refresh_token';
  private platformId = inject(PLATFORM_ID);

  // Use signal for user state
  private userSignal = signal<User | null>(null);
  public user = this.userSignal.asReadonly();
  public isAuthenticated = computed(() => !!this.userSignal());
  public isStoreManager = computed(() => this.userSignal()?.roles.includes('Store Manager') ?? false);
  public isAdmin = computed(() => this.userSignal()?.roles.includes('Admin') ?? false);

  constructor(private http: HttpClient, private router: Router) {
    if (isPlatformBrowser(this.platformId)) {
      const token = this.getToken();
      if (token) {
        // Initialize with token only, then fetch profile
        this.userSignal.set({ username: '', roles: [], token });
        this.fetchUserProfile().subscribe();
      }
    }
  }

  login(credentials: any): Observable<any> {
    return this.http.post(`${this.baseUrl}login/`, credentials).pipe(
      tap((response: any) => {
        if (isPlatformBrowser(this.platformId)) {
            localStorage.setItem(this.refreshTokenKey, response.refresh);
        }
        this.updateUserState(response.access, response.username, response.roles);
      })
    );
  }

  fetchUserProfile(): Observable<any> {
    return this.http.get(`${this.baseUrl}profile/`).pipe(
      tap((response: any) => {
        const token = this.getToken();
        if (token) {
            this.updateUserState(token, response.username, response.roles);
        }
      }),
      catchError(err => {
          if (err.status === 401) {
              return this.refreshToken().pipe(
                  switchMap((newToken: string | null) => {
                      if (newToken) {
                          // Retry profile fetch with new token
                          return this.fetchUserProfile();
                      }
                      this.logout();
                      return of(null);
                  })
              );
          }
          console.error('Profile fetch failed', err);
          this.logout();
          return of(null);
      })
    );
  }

  refreshToken(): Observable<string | null> {
      if (!isPlatformBrowser(this.platformId)) return of(null);

      const refresh = localStorage.getItem(this.refreshTokenKey);
      if (!refresh) return of(null);

      return this.http.post(`${this.baseUrl}token/refresh/`, { refresh }).pipe(
          tap((response: any) => {
              localStorage.setItem(this.tokenKey, response.access);
              // Handle refresh token rotation if backend returns a new refresh token
              if (response.refresh) {
                  localStorage.setItem(this.refreshTokenKey, response.refresh);
              }
              const currentUser = this.userSignal();
              if (currentUser) {
                  this.userSignal.set({ ...currentUser, token: response.access });
              }
          }),
          switchMap((response: any) => of(response.access)),
          catchError(() => {
              this.logout();
              return of(null);
          })
      );
  }

  private updateUserState(token: string, username: string, roles: string[]) {
      const user: User = { username, roles, token };
      if (isPlatformBrowser(this.platformId)) {
          localStorage.setItem(this.tokenKey, token);
      }
      this.userSignal.set(user);
  }

  logout() {
    if (isPlatformBrowser(this.platformId)) {
      localStorage.removeItem(this.tokenKey);
      localStorage.removeItem(this.refreshTokenKey);
    }
    this.userSignal.set(null);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    if (isPlatformBrowser(this.platformId)) {
      return localStorage.getItem(this.tokenKey);
    }
    return null;
  }
}
