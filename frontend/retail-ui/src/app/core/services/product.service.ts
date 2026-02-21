import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../constants/api.constants';

// Product and Store interfaces for type safety
export interface Product {
  id?: number;
  sku: string;
  product_name: string;
  price: number;
  date: string;
  store_id: number;
  store?: Store;
  // Add other fields as needed
}

export interface Store {
  id: number;
  name: string;
}

@Injectable({
  providedIn: 'root'
})
export class ProductService {
  private baseUrl = API_BASE_URL;

  constructor(private http: HttpClient) {}

  // Bulk update products by SKU from CSV file only
  uploadCSVForBulkUpdate(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post(`${this.baseUrl}price-feed/upload/`, formData);
  }

  // Get a single product by ID
  getProduct(id: number): Observable<any> {
    return this.http.get(`${this.baseUrl}price-feed/${id}/`);
  }

  // Update a single product (edit product details)
  updateProduct(product: Product): Observable<any> {
    const { id, ...payload } = product;
    if (id) {
      return this.http.put(`${this.baseUrl}price-feed/${id}/`, payload);
    }
    return this.http.put(`${this.baseUrl}price-feed/update/`, payload);
  }

  // Delete a product by id
  deleteProduct(id: number): Observable<any> {
    return this.http.delete(`${this.baseUrl}price-feed/${id}/`);
  }

  // (Optional) Create a single product
  createProduct(product: Product): Observable<any> {
    return this.http.post(`${this.baseUrl}price-feed/`, product);
  }

  // Get status of a CSV task
  getTaskStatus(taskId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}price-feed/csv-task-status/${taskId}/`);
  }

  // Search products with filters
  searchProducts(params: any): Observable<any> {
    let httpParams = new HttpParams();
    Object.keys(params).forEach(key => {
      if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
        httpParams = httpParams.set(key, params[key]);
      }
    });
    return this.http.get<any>(`${this.baseUrl}price-feed/search/`, { params: httpParams });
  }

  // Get all stores
  getStores(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}stores/`);
  }

  // Create a new store
  createStore(store: Store): Observable<any> {
    return this.http.post(`${this.baseUrl}stores/`, store);
  }
}
