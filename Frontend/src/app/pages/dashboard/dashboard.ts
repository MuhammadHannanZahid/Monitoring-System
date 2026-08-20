import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { DashboardIncident } from '../../core/models';
import { RealtimeService } from '../../core/realtime.service';

@Component({
  selector: 'app-dashboard-page',
  imports: [DatePipe, DecimalPipe],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class DashboardPage {
  readonly realtime = inject(RealtimeService);
  readonly summary = this.realtime.summary;
  readonly incidents = this.realtime.incidents;
  readonly activity = this.realtime.activity;
  readonly loading = computed(() => this.realtime.snapshot() === null);
  readonly error = this.realtime.error;
  readonly overallUptime = computed(() => {
    const percentages = this.realtime
      .overviews()
      .filter((overview) => overview.is_active)
      .map((overview) => this.realtime.liveUptimePercentage(overview))
      .filter((value): value is number => value !== null);
    if (!percentages.length) return 0;
    return percentages.reduce((total, value) => total + value, 0) / percentages.length;
  });

  constructor() {
    this.realtime.connect();
  }

  loadDashboard(): void {
    this.realtime.reconnect();
  }

  formatDuration(seconds: number | null): string {
    if (seconds === null) return 'Ongoing';
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  }

  incidentDuration(incident: DashboardIncident): string {
    return this.formatDuration(this.realtime.liveIncidentDuration(incident));
  }
}
