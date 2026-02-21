import { Component, OnInit, effect, ChangeDetectorRef } from '@angular/core';
import { ProductService } from '../../../core/services/product.service';
import { AuthService } from '../../../core/services/auth.service';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-product-upload',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './product-upload.component.html',
  styleUrls: ['./product-upload.component.scss']
})
export class ProductUploadComponent implements OnInit {
  uploadStatus: string | null = null;
  errorMessage: string | null = null;
  isProcessing = false;
  isStoreManager = false;

  productForm: FormGroup;
  stores: any[] = [];
  selectedFile: File | null = null;

  constructor(
    private productService: ProductService,
    private authService: AuthService,
    private fb: FormBuilder,
    private cdr: ChangeDetectorRef
  ) {
    this.productForm = this.fb.group({
      store_id: ['', Validators.required],
      sku: ['', Validators.required],
      product_name: ['', Validators.required],
      price: ['', [Validators.required, Validators.min(0)]],
      date: ['', Validators.required]
    });

    // Use effect to reactively update isStoreManager when the signal changes
    effect(() => {
      this.isStoreManager = this.authService.isStoreManager();
      this.cdr.markForCheck(); // Ensure change detection runs after signal update
    });
  }

  ngOnInit() {
    // Initial check (though effect handles updates)
    this.isStoreManager = this.authService.isStoreManager();
    this.loadStores();
  }

  loadStores() {
      this.productService.getStores().subscribe({
          next: (res) => {
              // Handle standardized response { status: 'success', data: [...] } or direct array
              const data = res.data || res;
              // Ensure stores is always an array
              this.stores = Array.isArray(data) ? data : (data.results || []);
              this.cdr.markForCheck();
          },
          error: (err) => {
              console.error('Failed to load stores', err);
              this.stores = [];
              this.cdr.markForCheck();
          }
      });
  }

  onFileSelected(event: any) {
    const file: File = event.target.files[0];
    if (file) {
        this.selectedFile = file;
        this.errorMessage = null;
        this.uploadStatus = null;
    } else {
        this.selectedFile = null;
    }
  }

  onUploadCSV() {
    if (!this.isStoreManager) {
      this.errorMessage = 'You do not have permission to upload files.';
      return;
    }

    if (this.selectedFile) {
      this.uploadStatus = 'Uploading...';
      this.errorMessage = null;
      this.isProcessing = true;
      this.cdr.markForCheck();

      this.productService.uploadCSVForBulkUpdate(this.selectedFile).subscribe({
        next: (res) => {
          if (res.status === 'success' || res.status === 'Processing') {
             this.uploadStatus = `Uploaded. Task ID: ${res.task_id}. Processing...`;
             this.pollTaskStatus(res.task_id);
          } else {
             this.uploadStatus = null;
             this.errorMessage = `Upload failed: ${JSON.stringify(res.errors || res)}`;
             this.isProcessing = false;
          }
          this.cdr.markForCheck();
        },
        error: (error: HttpErrorResponse) => {
          this.uploadStatus = null;
          this.isProcessing = false;
          this.errorMessage = this.extractErrorMessage(error);
          this.cdr.markForCheck();
        }
      });
    }
  }

  onProductSubmit() {
      if (!this.isStoreManager) {
          this.errorMessage = 'You do not have permission to create products.';
          return;
      }
      if (this.productForm.valid) {
          this.isProcessing = true;
          this.errorMessage = null;
          this.uploadStatus = 'Creating product...';
          this.cdr.markForCheck();

          this.productService.createProduct(this.productForm.value).subscribe({
              next: (res) => {
                  this.isProcessing = false;
                  this.uploadStatus = 'Product created successfully!';
                  this.productForm.reset();
                  setTimeout(() => {
                      this.uploadStatus = null;
                      this.cdr.markForCheck();
                  }, 3000);
                  this.cdr.markForCheck();
              },
              error: (error: HttpErrorResponse) => {
                  this.isProcessing = false;
                  this.uploadStatus = null;
                  this.errorMessage = this.extractErrorMessage(error);
                  this.cdr.markForCheck();
              }
          });
      }
  }

  pollTaskStatus(taskId: string) {
    const interval = setInterval(() => {
      this.productService.getTaskStatus(taskId).subscribe({
        next: (res) => {
          if (res.status === 'completed') {
            this.uploadStatus = 'Completed! Data processed successfully.';
            if (res.result) {
                 this.uploadStatus += ` Created: ${res.result.created}, Updated: ${res.result.updated}`;
            }
            this.isProcessing = false;
            clearInterval(interval);
          } else if (res.status === 'error') {
            this.uploadStatus = null;
            this.errorMessage = `Processing Error: ${res.error}`;
            this.isProcessing = false;
            clearInterval(interval);
          } else if (res.status === 'pending') {
             this.uploadStatus = `Processing... (Task ID: ${taskId})`;
          }
          this.cdr.markForCheck();
        },
        error: (error: HttpErrorResponse) => {
            this.uploadStatus = null;
            this.errorMessage = `Polling Error: ${this.extractErrorMessage(error)}`;
            this.isProcessing = false;
            clearInterval(interval);
            this.cdr.markForCheck();
        }
      });
    }, 2000);
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
      return error.message || 'An unknown error occurred.';
  }
}
