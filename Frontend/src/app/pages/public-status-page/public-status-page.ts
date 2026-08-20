import { DatePipe, DecimalPipe, isPlatformBrowser } from '@angular/common';
import { Component, DestroyRef, inject, PLATFORM_ID, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import {
  DailyUptime,
  PublicStatusMonitor,
  PublicStatusPage,
  PublicUptimeStatus,
} from '../../core/models';

@Component({
  selector: 'app-public-status-page',
  imports: [DatePipe, DecimalPipe, RouterLink],
  templateUrl: './public-status-page.html',
  styleUrl: './public-status-page.css',
})
export class PublicStatusPageView {
  private readonly destroyRef = inject(DestroyRef);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly slug = inject(ActivatedRoute).snapshot.paramMap.get('slug') ?? '';
  private source: EventSource | undefined;
  private clockTimer: ReturnType<typeof setInterval> | undefined;
  readonly page = signal<PublicStatusPage | null>(null);
  readonly loading = signal(true);
  readonly connected = signal(false);
  readonly error = signal('');
  readonly now = signal(Date.now());

  constructor() {
    if (isPlatformBrowser(this.platformId)) this.connect();
    this.destroyRef.onDestroy(() => {
      this.source?.close();
      if (this.clockTimer) clearInterval(this.clockTimer);
    });
  }

  overallLabel(status: PublicStatusPage['overall_status']): string {
    if (status === 'operational') return 'All systems operational';
    if (status === 'outage') return 'Service outage detected';
    if (status === 'degraded') return 'Some systems are degraded';
    return 'System status is pending';
  }

  serviceStatusLabel(status: PublicStatusPage['overall_status']): string {
    if (status === 'operational') return 'Operational';
    if (status === 'outage') return 'Outage';
    if (status === 'degraded') return 'Degraded';
    return 'Pending';
  }

  nextUpdateIn(page: PublicStatusPage): number {
    const interval = Math.max(1, page.refresh_interval_seconds);
    const elapsed = Math.max(0, Math.floor((this.now() - Date.parse(page.generated_at)) / 1000));
    return Math.max(0, interval - elapsed);
  }

  monitorStatus(monitor: PublicStatusMonitor): string {
    return monitor.is_active ? monitor.status : 'paused';
  }

  dayClass(day: DailyUptime): string {
    if (day.uptime_percentage === null) return 'no-data';
    if (day.uptime_percentage >= 100) return 'up';
    if (day.uptime_percentage <= 0) return 'down';
    return 'partial';
  }

  dayLabel(day: DailyUptime): string {
    const percentage =
      day.uptime_percentage === null ? 'No data' : `${day.uptime_percentage.toFixed(2)}% uptime`;
    return `${day.date} · ${percentage}`;
  }

  uptimeWindows(page: PublicStatusPage): Array<{
    label: string;
    value: number | null;
  }> {
    const uptime: PublicUptimeStatus = page.uptime_status;
    return [
      { label: 'Last 24 hours', value: uptime.last_24_hours },
      { label: 'Last 7 days', value: uptime.last_7_days },
      { label: 'Last 30 days', value: uptime.last_30_days },
      { label: 'Last 90 days', value: uptime.last_90_days },
    ];
  }

  private connect(): void {
    this.clockTimer = setInterval(() => this.now.set(Date.now()), 1000);
    const source = new EventSource(
      `/api/status-pages/public/${encodeURIComponent(this.slug)}/events`,
    );
    this.source = source;
    source.onopen = () => {
      this.connected.set(true);
      this.error.set('');
    };
    source.addEventListener('snapshot', (event) => {
      try {
        this.page.set(JSON.parse((event as MessageEvent<string>).data) as PublicStatusPage);
        this.loading.set(false);
        this.connected.set(true);
        this.error.set('');
      } catch {
        this.error.set('The latest status update could not be displayed.');
      }
    });
    source.addEventListener('deleted', () => {
      this.source?.close();
      this.connected.set(false);
      this.loading.set(false);
      this.page.set(null);
      this.error.set('This status page is no longer available.');
    });
    source.onerror = () => {
      this.connected.set(false);
      if (!this.page()) {
        this.loading.set(false);
        this.error.set('This status page is unavailable.');
      }
    };
  }
}
