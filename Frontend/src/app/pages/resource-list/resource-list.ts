import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, DestroyRef, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { MonitorOverview, RealtimeResources, ResourceRecord } from '../../core/models';
import { RealtimeService } from '../../core/realtime.service';

@Component({
  selector: 'app-resource-list-page',
  imports: [DatePipe, DecimalPipe, RouterLink],
  templateUrl: './resource-list.html',
  styleUrl: './resource-list.scss',
})
export class ResourceListPage {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(ApiService);
  private readonly realtime = inject(RealtimeService);
  private readonly destroyRef = inject(DestroyRef);
  readonly title = signal('Resources');
  readonly description = signal('');
  readonly newUrl = signal('');
  readonly detailBase = signal('');
  readonly deletePath = signal('');
  readonly updatePath = signal('');
  readonly records = signal<ResourceRecord[]>([]);
  readonly overviews = signal<Record<string, MonitorOverview>>({});
  readonly loading = signal(true);
  readonly deletingId = signal('');
  readonly updatingId = signal('');
  readonly error = signal('');
  readonly message = signal('');
  readonly heartbeatToken = signal('');
  readonly noticeLeaving = signal(false);
  private readonly resourceType = signal<keyof RealtimeResources | null>(null);
  private noticeTimer: ReturnType<typeof setTimeout> | undefined;
  private noticeRemovalTimer: ReturnType<typeof setTimeout> | undefined;

  constructor() {
    const navigationState = this.router.getCurrentNavigation()?.extras.state;
    const initialMessage = String(navigationState?.['message'] ?? '');
    const initialToken = String(navigationState?.['heartbeatToken'] ?? '');
    if (initialMessage || initialToken) this.showNotice(initialMessage, initialToken);
    this.destroyRef.onDestroy(() => this.clearNoticeTimers());
    this.realtime.connect();
    effect(() => {
      const error = this.realtime.error();
      if (error && this.loading()) this.error.set(error);
    });

    this.route.data.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((data) => {
      this.title.set(String(data['title'] ?? 'Resources'));
      this.description.set(String(data['description'] ?? ''));
      this.newUrl.set(String(data['newUrl'] ?? ''));
      this.detailBase.set(String(data['detailBase'] ?? ''));
      this.deletePath.set(String(data['deletePath'] ?? ''));
      this.updatePath.set(String(data['updatePath'] ?? ''));
      this.resourceType.set(data['resourceType'] as keyof RealtimeResources);
    });

    this.realtime.snapshots$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((snapshot) => {
      const resourceType = this.resourceType();
      if (!resourceType || !snapshot.resources) return;
      this.records.set(snapshot.resources[resourceType] as ResourceRecord[]);
      this.overviews.set(
        Object.fromEntries(snapshot.overviews.map((overview) => [overview.id, overview])),
      );
      this.error.set('');
      this.loading.set(false);
    });
  }

  target(record: ResourceRecord): string {
    if (record.url) return record.url;
    if (record.host) return record.host;
    if (record.login_url) return record.login_url;
    if (record.expected_heartbeat_interval) return `Every ${record.expected_heartbeat_interval}s`;
    return 'Configured';
  }

  overview(record: ResourceRecord): MonitorOverview | undefined {
    return this.overviews()[record.id];
  }

  deleteResource(record: ResourceRecord): void {
    if (!window.confirm(`Delete “${record.name}”? This action cannot be undone.`)) return;
    this.deletingId.set(record.id);
    const endpoint = this.deletePath().replace(':id', record.id);
    this.api.delete<null>(endpoint).subscribe({
      next: (response) => {
        this.records.update((records) => records.filter((item) => item.id !== record.id));
        this.showNotice(response.message);
        this.deletingId.set('');
      },
      error: (error: unknown) => {
        this.error.set(ApiService.errorMessage(error));
        this.deletingId.set('');
      },
    });
  }

  toggleActive(record: ResourceRecord): void {
    const stats = this.overview(record);
    if (!stats) return;
    this.updatingId.set(record.id);
    const endpoint = this.updatePath().replace(':id', record.id);
    this.api
      .put<unknown, { is_active: boolean }>(endpoint, { is_active: !stats.is_active })
      .subscribe({
        next: (response) => {
          const isActive = !stats.is_active;
          this.overviews.update((overviews) => ({
            ...overviews,
            [record.id]: this.realtime.withActiveState(stats, isActive),
          }));
          this.records.update((records) =>
            records.map((item) =>
              item.id === record.id ? { ...item, is_active: isActive } : item,
            ),
          );
          this.showNotice(response.message);
          this.updatingId.set('');
        },
        error: (error: unknown) => {
          this.error.set(ApiService.errorMessage(error));
          this.updatingId.set('');
        },
      });
  }

  private showNotice(message: string, heartbeatToken = ''): void {
    this.clearNoticeTimers();
    this.noticeLeaving.set(false);
    this.message.set(message);
    this.heartbeatToken.set(heartbeatToken);
    this.noticeTimer = setTimeout(
      () => {
        this.noticeLeaving.set(true);
        this.noticeRemovalTimer = setTimeout(() => {
          this.message.set('');
          this.heartbeatToken.set('');
          this.noticeLeaving.set(false);
        }, 260);
      },
      heartbeatToken ? 12000 : 4000,
    );
  }

  private clearNoticeTimers(): void {
    if (this.noticeTimer) clearTimeout(this.noticeTimer);
    if (this.noticeRemovalTimer) clearTimeout(this.noticeRemovalTimer);
  }

  formatDuration(totalSeconds: number): string {
    if (totalSeconds < 60) return `${totalSeconds}s`;
    if (totalSeconds < 3600) return `${Math.floor(totalSeconds / 60)}m`;
    if (totalSeconds < 86400)
      return `${Math.floor(totalSeconds / 3600)}h ${Math.floor((totalSeconds % 3600) / 60)}m`;
    return `${Math.floor(totalSeconds / 86400)}d ${Math.floor((totalSeconds % 86400) / 3600)}h`;
  }

  uptimeSeconds(overview: MonitorOverview): number {
    return this.realtime.liveUptimeSeconds(overview);
  }

  downtimeSeconds(overview: MonitorOverview): number {
    return this.realtime.liveDowntimeSeconds(overview);
  }

  uptimePercentage(overview: MonitorOverview): number | null {
    return this.realtime.liveUptimePercentage(overview);
  }
}
