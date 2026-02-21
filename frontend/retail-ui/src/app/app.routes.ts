import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { ProductListComponent } from './features/products/product-list/product-list.component';
import { ProductUploadComponent } from './features/products/product-upload/product-upload.component';
import { ProductEditComponent } from './features/products/product-edit/product-edit.component';
import { StoreListComponent } from './features/stores/store-list/store-list.component';
import { AuthGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  {
    path: '',
    component: DashboardComponent,
    canActivate: [AuthGuard],
    children: [
      { path: 'products', component: ProductListComponent },
      { path: 'products/upload', component: ProductUploadComponent },
      { path: 'products/edit/:id', component: ProductEditComponent },
      { path: 'stores', component: StoreListComponent },
      { path: '', redirectTo: 'products', pathMatch: 'full' }
    ]
  },
  { path: '**', redirectTo: 'login' }
];
