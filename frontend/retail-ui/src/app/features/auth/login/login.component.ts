import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { Router, ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent implements OnInit {
  loginForm: FormGroup;
  error: string | null = null;
  returnUrl: string = '/';
  isLoading = false;

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    this.loginForm = this.fb.group({
      username: ['', Validators.required],
      password: ['', Validators.required]
    });
  }

  ngOnInit(): void {
    // If already logged in, redirect to dashboard
    if (this.authService.getToken()) {
      this.router.navigate(['/']);
      return;
    }

    // Get return url from route parameters or default to '/'
    this.returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/';
  }

  onSubmit() {
    if (this.loginForm.valid) {
      this.isLoading = true;
      this.error = null;
      this.authService.login(this.loginForm.value).subscribe({
        next: () => {
             this.isLoading = false;
             this.router.navigateByUrl(this.returnUrl);
        },
        error: (err) => {
            this.isLoading = false;
            this.error = 'Invalid credentials';
        }
      });
    }
  }
}
