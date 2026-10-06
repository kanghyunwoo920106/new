"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Post } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function AdminPostsPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string>("");

  async function load() {
    try {
      setPosts(await api.listPosts());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function publish(id: string) {
    setBusy(id);
    setError("");
    try {
      await api.publishNow(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Publish failed");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-[family-name:var(--font-display)] text-2xl">글 목록</h2>
        <p className="text-sm text-[var(--brand-ink-soft)]">생성·검수·발행 상태를 확인합니다.</p>
      </div>
      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
      ) : null}
      {posts.length === 0 ? (
        <p className="text-sm text-[var(--brand-ink-soft)]">글이 없습니다. 생성·예약에서 배치를 만들어 보세요.</p>
      ) : (
        <ul className="space-y-3">
          {posts.map((p) => (
            <li key={p.id} className="rounded-md border border-[var(--brand-line)] bg-white/80 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary">{p.status}</Badge>
                    <Badge variant="outline">{p.category_name}</Badge>
                    {p.review_status !== "skipped" ? (
                      <Badge variant="outline">review: {p.review_status}</Badge>
                    ) : null}
                  </div>
                  <h3 className="mt-2 font-medium">{p.title}</h3>
                  <p className="mt-1 text-sm text-[var(--brand-ink-soft)]">
                    {p.char_count}자 · {p.model_id || "model"} · tags:{" "}
                    {p.seo_tags.map((t) => t.tag).join(", ") || "—"}
                  </p>
                </div>
                <div className="flex gap-2">
                  {p.status === "published_site" ? (
                    <Link
                      href={`/posts/${p.slug}`}
                      className="inline-flex h-7 items-center rounded-lg border border-border bg-background px-2.5 text-[0.8rem]"
                    >
                      보기
                    </Link>
                  ) : (
                    <Button size="sm" disabled={busy === p.id} onClick={() => publish(p.id)}>
                      {busy === p.id ? "발행 중…" : "즉시 발행"}
                    </Button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
