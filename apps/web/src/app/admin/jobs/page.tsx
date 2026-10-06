"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type PublishJob } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function AdminJobsPage() {
  const [jobs, setJobs] = useState<PublishJob[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      setJobs(await api.listJobs());
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, []);

  async function cancel(id: string) {
    try {
      await api.cancelJob(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cancel failed");
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-tight">발행 큐</h2>
        <p className="mt-1 text-sm text-[var(--brand-ink-soft)]">
          `publish_jobs.run_at`이 진실 원천입니다. Beat/APScheduler가 due job을 폴링해 자체 사이트에 발행합니다.
        </p>
      </div>
      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
      ) : null}
      {loading ? (
        <ul className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <li key={i} className="h-20 animate-pulse rounded-md bg-white/70" />
          ))}
        </ul>
      ) : jobs.length === 0 ? (
        <div className="rounded-md border border-dashed border-[var(--brand-line)] bg-white/70 px-5 py-10 text-center">
          <p className="font-medium">예약된 잡이 없습니다</p>
          <p className="mt-1 text-sm text-[var(--brand-ink-soft)]">생성·예약에서 배치를 만들면 여기에 쌓입니다.</p>
          <Link href="/admin/generate" className="mt-3 inline-block text-sm text-[var(--brand-teal)]">
            생성·예약으로 이동 →
          </Link>
        </div>
      ) : (
        <ul className="space-y-3">
          {jobs.map((j) => (
            <li key={j.id} className="rounded-md border border-[var(--brand-line)] bg-white/85 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary">{j.status}</Badge>
                    <Badge variant="outline">{j.channel_code}</Badge>
                  </div>
                  <p className="mt-2 font-medium">{j.post_title || j.post_id}</p>
                  <p className="mt-1 text-sm text-[var(--brand-ink-soft)]">
                    run_at: {new Date(j.run_at).toLocaleString("ko-KR")} · attempt {j.attempt}
                  </p>
                  {j.result_payload?.url ? (
                    <a
                      href={String(j.result_payload.url)}
                      className="text-sm text-[var(--brand-teal)]"
                      target="_blank"
                      rel="noreferrer"
                    >
                      {String(j.result_payload.url)}
                    </a>
                  ) : null}
                  {j.post_slug && j.status === "succeeded" ? (
                    <div>
                      <Link href={`/posts/${j.post_slug}`} className="text-sm text-[var(--brand-teal)]">
                        공개 글 보기 →
                      </Link>
                    </div>
                  ) : null}
                  {j.last_error ? <p className="mt-1 text-sm text-red-700">{j.last_error}</p> : null}
                </div>
                {j.status === "queued" ? (
                  <Button size="sm" variant="outline" onClick={() => cancel(j.id)}>
                    취소
                  </Button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
