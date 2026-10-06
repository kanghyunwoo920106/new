import Link from "next/link";
import { api } from "@/lib/api";

export default async function AdminHome() {
  let health;
  let postsCount = 0;
  let published = 0;
  let queued = 0;
  let error: string | undefined;
  try {
    health = await api.health();
    const [posts, jobs] = await Promise.all([api.listPosts(), api.listJobs("queued")]);
    postsCount = posts.length;
    published = posts.filter((p) => p.status === "published_site").length;
    queued = jobs.length;
  } catch (e) {
    error = e instanceof Error ? e.message : "API unreachable";
  }

  return (
    <div className="space-y-6">
      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <p className="font-medium">API 연결 실패</p>
          <p className="mt-1">{error}</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Claude" value={health?.mock_claude ? "Mock" : "Live"} hint={health?.mock_claude ? "ANTHROPIC_API_KEY 없음" : "Haiku + Sonnet sample"} />
          <Stat label="Scheduler" value={health?.scheduler || "—"} hint={health?.database || ""} />
          <Stat label="글 / 공개" value={`${postsCount} / ${published}`} hint="전체 초안 대비 공개" />
          <Stat label="대기 발행" value={String(queued)} hint="queued publish_jobs" />
        </div>
      )}

      <div className="rounded-md border border-[var(--brand-line)] bg-white/85 p-5">
        <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-tight">워크플로</h2>
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-[var(--brand-ink-soft)]">
          <li>허용 카테고리 선택 → AI가 주제 10개 추천</li>
          <li>주제 선택 → 2,000자+ 본문·SEO 태그 일괄 생성 (첫 글 + ~15% Sonnet 샘플 검수)</li>
          <li>즉시 발행 또는 sequential_cycle 예약 (4h / 12h / 24h / 2d / 1w)</li>
          <li>Celery Beat 또는 APScheduler가 due job을 자체 사이트에 발행</li>
        </ol>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href="/admin/generate"
            className="inline-flex rounded-md bg-[var(--brand-teal)] px-4 py-2 text-sm font-medium text-white transition hover:-translate-y-0.5"
          >
            생성·예약 시작
          </Link>
          <Link
            href="/admin/jobs"
            className="inline-flex rounded-md border border-[var(--brand-line)] bg-white px-4 py-2 text-sm text-[var(--brand-ink)]"
          >
            발행 큐 보기
          </Link>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-md border border-[var(--brand-line)] bg-white/85 p-4">
      <p className="text-xs tracking-wide text-[var(--brand-ink-soft)] uppercase">{label}</p>
      <p className="mt-2 font-[family-name:var(--font-display)] text-2xl tracking-tight">{value}</p>
      <p className="mt-1 text-xs text-[var(--brand-ink-soft)]">{hint}</p>
    </div>
  );
}
