import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { ProductService, Product } from '../../../core/services/product.service';
import { AuthService } from '../../../core/services/auth.service';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

@Component({
  selector: 'app-product-list',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './product-list.component.html',
  styleUrls: ['./product-list.component.scss']
})
export class ProductListComponent implements OnInit {
  products: Product[] = [];
  searchForm: FormGroup;
  loading = false;
  noDataFound = false;
  isStoreManager = false;

  // Pagination state
  currentPage = 1;
  pageSize = 10;
  totalCount = 0;
  totalPages = 1;
  nextPageUrl: string | null = null;
  prevPageUrl: string | null = null;

  // Internationalization state (currency only)
  userCurrency = 'INR'; // Default is INR, can be changed by user
  userLocale = navigator.language || 'en-IN'; // Use browser locale for date formatting
  availableCurrencies = [
    { code: 'INR', label: 'Indian Rupee' },
    { code: 'USD', label: 'US Dollar' },
    { code: 'EUR', label: 'Euro' }
  ];

  constructor(
    private productService: ProductService,
    private fb: FormBuilder,
    private cdr: ChangeDetectorRef,
    private router: Router,
    private authService: AuthService
  ) {
    this.searchForm = this.fb.group({
      search: [''],
      sku: [''],
      store_name: [''],
      min_price: [''],
      max_price: [''],
      ordering: ['relevance']
    });
    this.isStoreManager = this.authService.isStoreManager();
  }

  ngOnInit(): void {
    // Default currency is INR
    this.userCurrency = 'INR';
    this.loadProducts();
  }

  loadProducts(page: number = 1) {
    this.loading = true;
    this.noDataFound = false;
    this.products = [];
    this.currentPage = page;

    // Map frontend form fields to backend filter params
    const formValue = this.searchForm.value;
    const params: any = {
      ...formValue,
      page: this.currentPage,
      page_size: this.pageSize
    };
    // Remove empty ordering (default relevance)
    if (!params.ordering || params.ordering === 'relevance') {
      delete params.ordering;
    } else if (params.ordering === 'price_asc') {
      params.ordering = 'price';
    } else if (params.ordering === 'price_desc') {
      params.ordering = '-price';
    }
    this.productService.searchProducts(params).subscribe({
      next: (data) => {
        // Handle paginated response
        const results = Array.isArray(data) ? data : (data.results || []);
        this.products = results;
        this.totalCount = data.count || results.length;
        this.nextPageUrl = data.next || null;
        this.prevPageUrl = data.previous || null;
        this.totalPages = Math.ceil(this.totalCount / this.pageSize);
        this.loading = false;
        this.noDataFound = this.products.length === 0;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.noDataFound = true;
        this.cdr.markForCheck();
      }
    });
  }

  onCurrencyChange(event: Event) {
    const selectElement = event.target as HTMLSelectElement;
    if (selectElement && selectElement.value) {
      this.userCurrency = selectElement.value;
    }
  }

  onSearch() {
    this.loadProducts(1); // Reset to first page on search
  }

  onEdit(product: Product) {
    this.router.navigate(['/products/edit', product.id]);
  }

  onDelete(product: Product) {
    if (confirm(`Are you sure you want to delete ${product.product_name}?`)) {
      this.productService.deleteProduct(product.id!).subscribe({
        next: () => {
          this.loadProducts(this.currentPage);
        },
        error: (err) => {
          console.error('Failed to delete product', err);
          alert('Failed to delete product');
        }
      });
    }
  }

  // Pagination controls
  goToPage(page: number) {
    if (page >= 1 && page <= this.totalPages) {
      this.loadProducts(page);
    }
  }
  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.goToPage(this.currentPage + 1);
    }
  }
  prevPage() {
    if (this.currentPage > 1) {
      this.goToPage(this.currentPage - 1);
    }
  }
}
