'use client';

import { useEffect, useState } from 'react';
import { PhoneCall, CheckCircle, XCircle } from 'lucide-react';

interface CallAnalytics {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  recent_calls: Array<{
    call_id: string;
    channel: string;
    outcome: string;
    ended_at: string;
  }>;
}

export default function AnalyticsDashboard() {
  const [data, setData] = useState<CallAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/analytics');
      if (!res.ok) throw new Error('Failed to fetch analytics');
      const json = await res.json();
      setData(json);
    } catch (err: any) {
      setError(err.message || 'Unable to load call analytics right now.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  return (
    <div className="min-h-screen bg-background p-8 pt-24 text-foreground">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-3xl font-bold tracking-tight">FinSaathi Call Analytics</h1>
          <button
            onClick={fetchAnalytics}
            disabled={loading}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            {loading ? 'Refreshing...' : 'Refresh Data'}
          </button>
        </div>

        {error ? (
          <div className="rounded-lg border border-red-500/50 bg-red-500/10 p-6 text-center text-red-500">
            <p className="font-semibold">{error}</p>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-3">
            {/* Total Calls Card */}
            <div className="flex flex-col rounded-xl border bg-card p-6 shadow-sm">
              <div className="flex items-center gap-4">
                <div className="rounded-full bg-blue-500/20 p-3">
                  <PhoneCall className="size-6 text-blue-500" />
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Total Calls</p>
                  <h3 className="text-3xl font-bold">{data?.total_calls ?? '-'}</h3>
                </div>
              </div>
            </div>

            {/* Successful Calls Card */}
            <div className="flex flex-col rounded-xl border bg-card p-6 shadow-sm">
              <div className="flex items-center gap-4">
                <div className="rounded-full bg-green-500/20 p-3">
                  <CheckCircle className="size-6 text-green-500" />
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Successful Calls</p>
                  <h3 className="text-3xl font-bold">{data?.successful_calls ?? '-'}</h3>
                </div>
              </div>
            </div>

            {/* Failed Calls Card */}
            <div className="flex flex-col rounded-xl border bg-card p-6 shadow-sm">
              <div className="flex items-center gap-4">
                <div className="rounded-full bg-red-500/20 p-3">
                  <XCircle className="size-6 text-red-500" />
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Failed Calls</p>
                  <h3 className="text-3xl font-bold">{data?.failed_calls ?? '-'}</h3>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Optional Recent Calls Table */}
        {!error && data?.recent_calls && data.recent_calls.length > 0 && (
          <div className="mt-12 overflow-hidden rounded-xl border bg-card shadow-sm">
            <div className="border-b bg-muted/50 p-4">
              <h3 className="font-semibold">Recent Calls</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-muted/20">
                  <tr>
                    <th className="px-6 py-3 font-medium text-muted-foreground">Time</th>
                    <th className="px-6 py-3 font-medium text-muted-foreground">Channel</th>
                    <th className="px-6 py-3 font-medium text-muted-foreground">Outcome</th>
                    <th className="px-6 py-3 font-medium text-muted-foreground">Call ID</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.recent_calls.map((call, idx) => (
                    <tr key={idx} className="transition-colors hover:bg-muted/10">
                      <td className="px-6 py-4 whitespace-nowrap">
                        {new Date(call.ended_at).toLocaleTimeString()}
                      </td>
                      <td className="px-6 py-4 uppercase">
                        <span className="inline-flex rounded-full bg-secondary px-2.5 py-0.5 text-xs font-semibold">
                          {call.channel}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {call.outcome === 'success' ? (
                          <span className="inline-flex items-center gap-1.5 text-green-500">
                            <CheckCircle className="size-4" /> Success
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-red-500">
                            <XCircle className="size-4" /> Failed
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 font-mono text-xs text-muted-foreground">
                        {call.call_id.substring(0, 16)}...
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
