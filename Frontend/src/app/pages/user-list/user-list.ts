import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { UserResponse } from '../../core/models';

@Component({
  selector: 'app-user-list-page',
  imports: [DatePipe, RouterLink],
  templateUrl: './user-list.html',
  styleUrl: './user-list.scss',
})
export class UserListPage {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  readonly users = signal<UserResponse[]>([]);
  readonly loading = signal(true);
  readonly updatingId = signal('');
  readonly deletingId = signal('');
  readonly error = signal('');
  readonly message = signal('');
  readonly noticeLeaving = signal(false);
  private noticeTimer: ReturnType<typeof setTimeout> | undefined;
  private noticeRemovalTimer: ReturnType<typeof setTimeout> | undefined;

  constructor() {
    const navigationMessage = String(
      this.router.getCurrentNavigation()?.extras.state?.['message'] ?? '',
    );
    if (navigationMessage) this.showNotice(navigationMessage);
    this.destroyRef.onDestroy(() => this.clearNoticeTimers());
    this.loadUsers();
  }

  toggleActive(user: UserResponse): void {
    if (user.role === 'admin') return;
    this.updatingId.set(user.id);
    this.api
      .put<UserResponse, { is_active: boolean }>(`/users/${user.id}/update`, {
        is_active: !user.is_active,
      })
      .subscribe({
        next: (response) => {
          this.users.update((users) =>
            users.map((item) => (item.id === user.id ? response.data : item)),
          );
          this.updatingId.set('');
          this.showNotice(
            `${response.data.username} was ${response.data.is_active ? 'activated' : 'deactivated'}.`,
          );
        },
        error: (error: unknown) => {
          this.error.set(ApiService.errorMessage(error));
          this.updatingId.set('');
        },
      });
  }

  deleteUser(user: UserResponse): void {
    if (user.role === 'admin') return;
    if (!window.confirm(`Delete “${user.username}”? This action cannot be undone.`)) return;
    this.deletingId.set(user.id);
    this.api.delete<null>(`/users/${user.id}/delete`).subscribe({
      next: (response) => {
        this.users.update((users) => users.filter((item) => item.id !== user.id));
        this.deletingId.set('');
        this.showNotice(response.message);
      },
      error: (error: unknown) => {
        this.error.set(ApiService.errorMessage(error));
        this.deletingId.set('');
      },
    });
  }

  private loadUsers(): void {
    this.api.get<UserResponse[]>('/users/list').subscribe({
      next: (response) => {
        this.users.set(response.data.filter((user) => user.role === 'viewer'));
        this.loading.set(false);
      },
      error: (error: unknown) => {
        this.error.set(ApiService.errorMessage(error));
        this.loading.set(false);
      },
    });
  }

  private showNotice(message: string): void {
    this.clearNoticeTimers();
    this.noticeLeaving.set(false);
    this.message.set(message);
    this.noticeTimer = setTimeout(() => {
      this.noticeLeaving.set(true);
      this.noticeRemovalTimer = setTimeout(() => {
        this.message.set('');
        this.noticeLeaving.set(false);
      }, 260);
    }, 4000);
  }

  private clearNoticeTimers(): void {
    if (this.noticeTimer) clearTimeout(this.noticeTimer);
    if (this.noticeRemovalTimer) clearTimeout(this.noticeRemovalTimer);
  }
}
