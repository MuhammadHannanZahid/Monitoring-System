import { Component, DestroyRef, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { CreateUserRequest, UserResponse } from '../../core/models';

@Component({
  selector: 'app-register-user-page',
  imports: [ReactiveFormsModule],
  templateUrl: './register-user.html',
  styleUrl: './register-user.scss',
})
export class RegisterUserPage {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(ApiService);
  private readonly destroyRef = inject(DestroyRef);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly success = signal('');
  readonly noticeLeaving = signal(false);
  private noticeTimer: ReturnType<typeof setTimeout> | undefined;
  private noticeRemovalTimer: ReturnType<typeof setTimeout> | undefined;

  readonly form = this.fb.nonNullable.group({
    username: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(50)]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    role: this.fb.nonNullable.control<'admin' | 'viewer'>('viewer'),
  });

  constructor() {
    this.destroyRef.onDestroy(() => {
      if (this.noticeTimer) clearTimeout(this.noticeTimer);
      if (this.noticeRemovalTimer) clearTimeout(this.noticeRemovalTimer);
    });
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading.set(true);
    this.error.set('');
    this.success.set('');
    const request: CreateUserRequest = this.form.getRawValue();
    this.api
      .post<UserResponse, CreateUserRequest>('/users/create', request)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (response) => {
          this.showSuccess(`${response.data.username} was registered as ${response.data.role}.`);
          this.form.reset({ username: '', password: '', role: 'viewer' });
        },
        error: (error: unknown) => this.error.set(ApiService.errorMessage(error)),
      });
  }

  private showSuccess(message: string): void {
    if (this.noticeTimer) clearTimeout(this.noticeTimer);
    if (this.noticeRemovalTimer) clearTimeout(this.noticeRemovalTimer);
    this.noticeLeaving.set(false);
    this.success.set(message);
    this.noticeTimer = setTimeout(() => {
      this.noticeLeaving.set(true);
      this.noticeRemovalTimer = setTimeout(() => {
        this.success.set('');
        this.noticeLeaving.set(false);
      }, 260);
    }, 4000);
  }
}
