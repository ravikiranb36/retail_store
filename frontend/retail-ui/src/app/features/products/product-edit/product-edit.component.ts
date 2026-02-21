import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ProductService, Product, Store } from '../../../core/services/product.service';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

@Component({
  selector: 'app-product-edit',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './product-edit.component.html',
  styleUrls: ['./product-edit.component.scss']
})
export class ProductEditComponent implements OnInit {
  editForm: FormGroup;
  productId: number | null = null;
  stores: Store[] = [];
  isLoading = false;
  isProcessing = false;
  errorMessage: string | null = null;
  successMessage: string | null = null;

  constructor(
    private fb: FormBuilder,
    private productService: ProductService,
    private route: ActivatedRoute,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {
    this.editForm = this.fb.group({
      sku: ['', Validators.required],
      product_name: ['', Validators.required],
      price: ['', [Validators.required, Validators.min(0)]],
      date: ['', Validators.required],
      store_id: ['', Validators.required]
    });
  }

  ngOnInit(): void {
    this.loadStores();
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.productId = +id;
      this.loadProduct(this.productId);
    }
  }

  loadStores() {
    this.productService.getStores().subscribe({
      next: (data) => {
        // Handle paginated or list response
        this.stores = Array.isArray(data) ? data : (data.results || []);
        this.cdr.markForCheck();
      },
      error: (err) => console.error('Failed to load stores', err)
    });
  }

  loadProduct(id: number) {
    this.isLoading = true;
    this.productService.getProduct(id).subscribe({
      next: (response) => {
        const product = response.data;
        this.editForm.patchValue({
          sku: product.sku,
          product_name: product.product_name,
          price: product.price,
          date: product.date,
          store_id: product.store?.id || product.store_id
        });
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Failed to load product', err);
        this.errorMessage = 'Failed to load product details.';
        this.isLoading = false;
        this.cdr.markForCheck();
      }
    });
  }

  onSubmit() {
    if (this.editForm.valid && this.productId) {
      this.isProcessing = true;
      this.errorMessage = null;
      this.successMessage = null;

      this.productService.updateProduct({ id: this.productId, ...this.editForm.value }).subscribe({
        next: () => {
          this.isProcessing = false;
          this.successMessage = 'Product updated successfully!';
          this.cdr.markForCheck();
          setTimeout(() => this.router.navigate(['/products']), 1500);
        },
        error: (error: HttpErrorResponse) => {
          this.isProcessing = false;
          this.errorMessage = this.extractErrorMessage(error);
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
        return JSON.stringify(error.error);
      }
    }
    return error.message || 'An unknown error occurred.';
  }
}
