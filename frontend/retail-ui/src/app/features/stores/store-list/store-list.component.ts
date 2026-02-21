import { Component, OnInit, effect, ChangeDetectorRef } from '@angular/core';
import { ProductService } from '../../../core/services/product.service';
import { AuthService } from '../../../core/services/auth.service';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';

@Component({
  selector: 'app-store-list',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './store-list.component.html',
  styleUrls: ['./store-list.component.scss']
})
export class StoreListComponent implements OnInit {
  stores: any[] = [];
  storeForm: FormGroup;
  loading = false;
  error: string | null = null;
  isAdmin = false;

  constructor(
    private productService: ProductService,
    private authService: AuthService,
    private fb: FormBuilder,
    private cdr: ChangeDetectorRef
  ) {
    this.storeForm = this.fb.group({
      name: ['', Validators.required]
    });

    effect(() => {
      this.isAdmin = this.authService.isAdmin();
      this.cdr.markForCheck();
    });
  }

  ngOnInit(): void {
    this.isAdmin = this.authService.isAdmin();
    this.loadStores();
  }

  loadStores() {
    this.loading = true;
    this.productService.getStores().subscribe({
      next: (res) => {
        const data = res.data || res;
        this.stores = Array.isArray(data) ? data : (data.results || []);
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  onSubmit() {
    if (!this.isAdmin) {
        this.error = 'Only Admins can create stores.';
        return;
    }

    if (this.storeForm.valid) {
      this.loading = true;
      this.error = null;
      this.productService.createStore(this.storeForm.value).subscribe({
        next: () => {
          this.loadStores();
          this.storeForm.reset();
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: (err: HttpErrorResponse) => {
            this.loading = false;
            this.error = this.extractErrorMessage(err);
            this.cdr.markForCheck();
        }
      });
    }
  }

  private extractErrorMessage(error: HttpErrorResponse): string {
      if (error.error) {
          if (typeof error.error === 'string') {
              return error.error;
          }
          if (typeof error.error === 'object') {
              if (error.error.detail) {
                  return error.error.detail;
              }
              if (error.error.errors) {
                  return JSON.stringify(error.error.errors);
              }
              return Object.entries(error.error)
                  .map(([key, value]) => `${key}: ${value}`)
                  .join(', ');
          }
      }
      return error.message || 'Failed to create store';
  }
}
