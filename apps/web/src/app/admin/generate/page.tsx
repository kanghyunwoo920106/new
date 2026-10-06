"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type Batch, type Category, type Topic } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

const CHANNELS = [
  { code: "site", label: "자체 사이트" },
  { code: "tistory", label: "티스토리" },
  { code: "blogger", label: "구글 블로거" },
] as const;

const INTERVALS = [
  { code: "4h", label: "4시간" },
  { code: "12h", label: "12시간" },
  { code: "24h", label: "24시간" },
  { code: "2d", label: "2일" },
  { code: "1w", label: "1주" },
] as const;

const INTERVAL_SECONDS: Record<string, number> = {
  "4h": 4 * 3600,
  "12h": 12 * 3600,
  "24h": 24 * 3600,
  "2d": 2 * 24 * 3600,
  "1w": 7 * 24 * 3600,
};

function previewTimes(first: string, codes: string[], count: number): Date[] {
  if (!first || count <= 0) return [];
  const sorted = [...codes].sort((a, b) => INTERVAL_SECONDS[a] - INTERVAL_SECONDS[b]);
  if (!sorted.length) return [];
  const times = [new Date(first)];
  let cursor = times[0];
  let i = 0;
  while (times.length < count) {
    cursor = new Date(cursor.getTime() + INTERVAL_SECONDS[sorted[i % sorted.length]] * 1000);
    times.push(cursor);
    i += 1;
  }
  return times;
}

function StepPill({ n, label, active, done }: { n: number; label: string; active?: boolean; done?: boolean }) {
  return (
    <div
      className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-sm ${
        active
          ? "bg-[var(--brand-teal)] text-white"
          : done
            ? "bg-[color-mix(in_oklab,var(--brand-mist)_90%,white)] text-[var(--brand-teal-deep)]"
            : "bg-white/60 text-[var(--brand-ink-soft)]"
      }`}
    >
      <span className="inline-flex size-5 items-center justify-center rounded-full bg-black/10 text-xs font-semibold">
        {done ? "✓" : n}
      </span>
      {label}
    </div>
  );
}

export default function GeneratePage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [categoryId, setCategoryId] = useState("");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [mockClaude, setMockClaude] = useState<boolean | null>(null);
  const [scheduler, setScheduler] = useState<string>("");
  const [publishMode, setPublishMode] = useState<"immediate" | "scheduled">("immediate");
  const [firstPublishAt, setFirstPublishAt] = useState("");
  const [intervals, setIntervals] = useState<Set<string>>(new Set(["4h", "24h"]));
  const [channels, setChannels] = useState<Set<string>>(new Set(["site"]));
  const [readyChannels, setReadyChannels] = useState<string[]>(["site"]);
  const [loading, setLoading] = useState("");
  const [loadError, setLoadError] = useState("");
  const [error, setError] = useState("");
  const [batch, setBatch] = useState<Batch | null>(null);
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    Promise.all([api.categories(), api.health()])
      .then(([rows, h]) => {
        setCategories(rows);
        if (rows[0]) setCategoryId(rows[0].id);
        setMockClaude(h.mock_claude);
        setScheduler(h.scheduler);
        if (h.configured_channels?.length) setReadyChannels(h.configured_channels);
      })
      .catch((e) => setLoadError(e instanceof Error ? e.message : "API unreachable"))
      .finally(() => setBooting(false));
  }, []);

  useEffect(() => {
    if (!batch || ["ready", "done", "failed"].includes(batch.status)) return;
    const t = setInterval(() => {
      api
        .getBatch(batch.id)
        .then(setBatch)
        .catch((e) => setError(e.message));
    }, 1500);
    return () => clearInterval(t);
  }, [batch]);

  const selectedCategory = useMemo(
    () => categories.find((c) => c.id === categoryId),
    [categories, categoryId],
  );

  const selectedCount = selected.size;
  const schedulePreview = useMemo(() => {
    if (publishMode !== "scheduled") return [];
    return previewTimes(firstPublishAt, Array.from(intervals), Math.max(selectedCount, 1));
  }, [publishMode, firstPublishAt, intervals, selectedCount]);

  const step = batch ? 4 : topics.length ? 3 : categoryId ? 2 : 1;

  async function recommend() {
    setError("");
    setLoading("recommend");
    setBatch(null);
    try {
      const res = await api.recommendTopics(categoryId);
      setTopics(res.topics);
      setSelected(new Set(res.topics.map((t) => t.id)));
      setMockClaude(res.mock_claude);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Recommend failed");
    } finally {
      setLoading("");
    }
  }

  function toggleTopic(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleChannel(code: string) {
    setChannels((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  function toggleInterval(code: string) {
    setIntervals((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  async function createBatch() {
    setError("");
    if (selected.size === 0) {
      setError("주제를 하나 이상 선택하세요.");
      return;
    }
    if (channels.size === 0) {
      setError("발행할 곳을 하나 이상 선택하세요.");
      return;
    }
    const unconfigured = Array.from(channels).filter((code) => !readyChannels.includes(code));
    if (unconfigured.length > 0) {
      setError(`${unconfigured.join(", ")} 토큰이 .env에 없습니다. 저장한 뒤 API를 다시 시작하세요.`);
      return;
    }
    if (publishMode === "scheduled") {
      if (!firstPublishAt) {
        setError("첫 발행 시각이 필요합니다.");
        return;
      }
      if (intervals.size === 0) {
        setError("간격을 하나 이상 선택하세요.");
        return;
      }
    }
    setLoading("batch");
    try {
      const body = {
        category_id: categoryId,
        topic_suggestion_ids: topics.filter((t) => selected.has(t.id)).map((t) => t.id),
        publish_mode: publishMode,
        first_publish_at:
          publishMode === "scheduled" ? new Date(firstPublishAt).toISOString() : null,
        interval_codes: Array.from(intervals),
        interval_mode: "sequential_cycle" as const,
        channels: Array.from(channels),
      };
      const created = await api.createBatch(body);
      setBatch(created);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Batch failed");
    } finally {
      setLoading("");
    }
  }

  if (booting) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 animate-pulse rounded bg-white/70" />
        <div className="h-40 animate-pulse rounded-md bg-white/70" />
        <div className="h-40 animate-pulse rounded-md bg-white/70" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 px-5 py-6">
        <p className="font-medium text-red-900">운영 API에 연결할 수 없습니다</p>
        <p className="mt-1 text-sm text-red-800">{loadError}</p>
        <p className="mt-3 text-sm text-red-800">API가 http://127.0.0.1:8471 에서 실행 중인지 확인하세요.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <StepPill n={1} label="카테고리" active={step === 1} done={step > 1} />
        <StepPill n={2} label="주제 추천" active={step === 2 && !topics.length} done={topics.length > 0} />
        <StepPill n={3} label="발행 설정" active={step === 3} done={!!batch} />
        <StepPill n={4} label="생성·큐" active={step === 4} done={batch?.status === "ready"} />
        <div className="ml-auto flex flex-wrap gap-2">
          {mockClaude !== null ? (
            <Badge variant="secondary">{mockClaude ? "Claude: mock" : "Claude: live"}</Badge>
          ) : null}
          {scheduler ? <Badge variant="outline">Scheduler: {scheduler}</Badge> : null}
        </div>
      </div>

      <section className="rounded-md border border-[var(--brand-line)] bg-white/85 p-5 shadow-[0_1px_0_rgba(22,52,58,0.04)]">
        <div>
          <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-tight">1. 카테고리</h2>
          <p className="mt-1 text-sm text-[var(--brand-ink-soft)]">
            비민감 allowlist만 표시됩니다. 의료·투자·법률·성인은 차단됩니다.
          </p>
        </div>
        {categories.length === 0 ? (
          <p className="mt-4 text-sm text-[var(--brand-ink-soft)]">등록된 카테고리가 없습니다.</p>
        ) : (
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {categories.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => {
                  setCategoryId(c.id);
                  setTopics([]);
                  setSelected(new Set());
                  setBatch(null);
                }}
                className={`rounded-md border px-4 py-3 text-left transition ${
                  categoryId === c.id
                    ? "border-[var(--brand-teal)] bg-[color-mix(in_oklab,var(--brand-mist)_80%,white)] ring-1 ring-[var(--brand-teal)]/30"
                    : "border-[var(--brand-line)] bg-white hover:border-[var(--brand-teal)]"
                }`}
              >
                <p className="font-medium">{c.name}</p>
                <p className="mt-1 text-xs leading-relaxed text-[var(--brand-ink-soft)]">{c.description}</p>
              </button>
            ))}
          </div>
        )}
        <Button className="mt-4" onClick={recommend} disabled={!categoryId || loading === "recommend"}>
          {loading === "recommend"
            ? "주제 추천 중…"
            : `${selectedCategory?.name || "카테고리"} · 주제 10개 추천`}
        </Button>
      </section>

      <section className="rounded-md border border-[var(--brand-line)] bg-white/85 p-5">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-tight">2. 주제 선택</h2>
            <p className="mt-1 text-sm text-[var(--brand-ink-soft)]">
              선택한 주제로 2,000자+ 글을 일괄 생성합니다. {topics.length ? `${selectedCount}/${topics.length} 선택` : ""}
            </p>
          </div>
          {topics.length > 0 ? (
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setSelected(new Set(topics.map((t) => t.id)))}
              >
                전체 선택
              </Button>
              <Button size="sm" variant="outline" onClick={() => setSelected(new Set())}>
                선택 해제
              </Button>
            </div>
          ) : null}
        </div>
        {loading === "recommend" ? (
          <ul className="mt-4 space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <li key={i} className="h-16 animate-pulse rounded-md bg-[var(--brand-mist)]/60" />
            ))}
          </ul>
        ) : topics.length === 0 ? (
          <div className="mt-4 rounded-md border border-dashed border-[var(--brand-line)] px-4 py-8 text-center">
            <p className="font-medium text-[var(--brand-ink)]">아직 추천된 주제가 없습니다</p>
            <p className="mt-1 text-sm text-[var(--brand-ink-soft)]">위에서 카테고리를 고른 뒤 주제 10개를 추천받으세요.</p>
          </div>
        ) : (
          <ul className="mt-4 space-y-3">
            {topics.map((t) => (
              <li key={t.id} className="flex gap-3 rounded-md border border-[var(--brand-line)] p-3 transition hover:bg-[var(--brand-sand)]/50">
                <Checkbox
                  checked={selected.has(t.id)}
                  onCheckedChange={() => toggleTopic(t.id)}
                  className="mt-1"
                />
                <div>
                  <p className="font-medium">{t.title}</p>
                  <p className="mt-1 text-sm text-[var(--brand-ink-soft)]">{t.angle}</p>
                  <p className="mt-1 text-xs text-[var(--brand-ink-soft)]">
                    SEO {t.score} · {(t.seed_keywords || []).join(", ")}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-md border border-[var(--brand-line)] bg-white/85 p-5">
        <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-tight">3. 발행 방식</h2>
        <p className="mt-1 text-sm text-[var(--brand-ink-soft)]">
          자체 사이트, 티스토리, 구글 블로거에 발행할 수 있습니다. 외부 채널은 .env 토큰이 있을 때만 켜집니다.
        </p>
        <div className="mt-4 flex flex-wrap gap-4">
          {CHANNELS.map((ch) => {
            const ready = readyChannels.includes(ch.code);
            return (
              <label key={ch.code} className="flex items-center gap-2 text-sm">
                <Checkbox checked={channels.has(ch.code)} onCheckedChange={() => toggleChannel(ch.code)} />
                {ch.label}
                {ready ? null : <span className="text-xs text-[var(--brand-ink-soft)]">토큰 없음</span>}
              </label>
            );
          })}
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <Button
            variant={publishMode === "immediate" ? "default" : "outline"}
            onClick={() => setPublishMode("immediate")}
          >
            즉시 발행
          </Button>
          <Button
            variant={publishMode === "scheduled" ? "default" : "outline"}
            onClick={() => setPublishMode("scheduled")}
          >
            예약 (sequential_cycle)
          </Button>
        </div>

        {publishMode === "scheduled" ? (
          <div className="mt-5 space-y-4 rounded-md border border-[var(--brand-line)] bg-[var(--brand-sand)]/40 p-4">
            <div>
              <Label htmlFor="first">첫 발행 시각</Label>
              <Input
                id="first"
                type="datetime-local"
                className="mt-1 max-w-sm bg-white"
                value={firstPublishAt}
                onChange={(e) => setFirstPublishAt(e.target.value)}
              />
            </div>
            <div>
              <Label>간격 다중선택</Label>
              <div className="mt-2 flex flex-wrap gap-3">
                {INTERVALS.map((iv) => (
                  <label key={iv.code} className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={intervals.has(iv.code)}
                      onCheckedChange={() => toggleInterval(iv.code)}
                    />
                    {iv.label}
                  </label>
                ))}
              </div>
            </div>
            {schedulePreview.length > 0 && firstPublishAt ? (
              <div>
                <p className="text-xs font-medium tracking-wide text-[var(--brand-ink-soft)] uppercase">
                  예상 발행 시각 (선택 {selectedCount || 1}편)
                </p>
                <ol className="mt-2 space-y-1 text-sm text-[var(--brand-ink)]">
                  {schedulePreview.slice(0, Math.max(selectedCount, 1)).map((d, i) => (
                    <li key={i}>
                      #{i + 1} · {d.toLocaleString("ko-KR")}
                    </li>
                  ))}
                </ol>
              </div>
            ) : (
              <p className="text-xs text-[var(--brand-ink-soft)]">첫 시각과 간격을 고르면 미리보기가 표시됩니다.</p>
            )}
          </div>
        ) : (
          <p className="mt-4 text-sm text-[var(--brand-ink-soft)]">
            생성 직후 발행 큐에 넣고, 스케줄러가 수 초 내에 공개 사이트에 올립니다.
          </p>
        )}

        <Button className="mt-5" onClick={createBatch} disabled={topics.length === 0 || loading === "batch"}>
          {loading === "batch" ? "배치 생성 중…" : `생성 시작 (${selectedCount}편)`}
        </Button>
      </section>

      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
      ) : null}

      {batch ? (
        <section className="rounded-md border border-[var(--brand-line)] bg-white/85 p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-[family-name:var(--font-display)] text-2xl tracking-tight">4. 배치 진행</h2>
            <Badge>{batch.status}</Badge>
          </div>
          <p className="mt-1 text-xs text-[var(--brand-ink-soft)]">id: {batch.id}</p>
          {["pending", "generating"].includes(batch.status) ? (
            <p className="mt-3 text-sm text-[var(--brand-ink-soft)]">글을 생성·검수하는 중입니다…</p>
          ) : null}
          <ul className="mt-4 space-y-2">
            {batch.items.map((item) => (
              <li key={item.id} className="rounded-md border border-[var(--brand-line)] px-3 py-2 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span>
                    #{item.sequence_index + 1} {item.post_title || item.topic_title}
                  </span>
                  <span className="text-[var(--brand-ink-soft)]">
                    {item.status}
                    {item.char_count ? ` · ${item.char_count}자` : ""}
                    {item.review_status && item.review_status !== "skipped"
                      ? ` · review:${item.review_status}`
                      : ""}
                  </span>
                </div>
                {item.post_slug && batch.status === "ready" ? (
                  <Link className="text-[var(--brand-teal)]" href={`/posts/${item.post_slug}`}>
                    공개 페이지 →
                  </Link>
                ) : null}
              </li>
            ))}
          </ul>
          {batch.status === "ready" ? (
            <p className="mt-4 text-sm text-[var(--brand-ink-soft)]">
              <Link href="/admin/jobs" className="text-[var(--brand-teal)]">
                발행 큐
              </Link>
              {" · "}
              <Link href="/" className="text-[var(--brand-teal)]">
                공개 블로그
              </Link>
            </p>
          ) : null}
          {batch.status === "failed" ? (
            <p className="mt-3 text-sm text-red-700">배치가 실패했습니다. 로그를 확인한 뒤 다시 시도하세요.</p>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
