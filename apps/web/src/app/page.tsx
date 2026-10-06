import Link from "next/link";
import { AdSenseSlot } from "@/components/adsense-slot";
import { SiteHeader } from "@/components/site-header";
import { api, type Post } from "@/lib/api";

async function loadPosts(): Promise<{ posts: Post[]; error?: string }> {
  try {
    const posts = await api.publicPosts();
    return { posts };
  } catch (e) {
    return { posts: [], error: e instanceof Error ? e.message : "Failed to load posts" };
  }
}

export default async function HomePage() {
  const { posts, error } = await loadPosts();

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main>
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-0">
            <div className="animate-drift absolute -top-16 right-[-10%] h-72 w-72 rounded-full bg-[radial-gradient(circle,rgba(15,110,106,0.28),transparent_70%)]" />
            <div className="absolute bottom-0 left-[-8%] h-64 w-64 rounded-full bg-[radial-gradient(circle,rgba(217,119,6,0.16),transparent_70%)]" />
          </div>
          <div className="relative mx-auto flex min-h-[70vh] max-w-5xl flex-col justify-end px-5 pb-16 pt-10 md:px-8 md:pb-20">
            <p className="animate-ink font-[family-name:var(--font-display)] text-5xl leading-[1.05] tracking-tight text-[var(--brand-ink)] md:text-7xl">
              루멘포스트
            </p>
            <h1 className="animate-rise mt-5 max-w-2xl text-xl font-medium text-[var(--brand-ink)] md:text-2xl">
              일상과 취미를 깊게 쓰는 AI 발행 블로그
            </h1>
            <p className="animate-rise-delay mt-3 max-w-xl text-[var(--brand-ink-soft)]">
              여행·요리·정리·문화 등 비민감 주제만. AdSense 승인 전에는 자리표시자 슬롯으로 준비합니다.
            </p>
            <div className="animate-rise-delay mt-8 flex flex-wrap gap-3">
              <Link
                href="/admin/generate"
                className="rounded-md bg-[var(--brand-teal)] px-4 py-2.5 text-sm font-medium text-white transition hover:-translate-y-0.5"
              >
                글 생성하기
              </Link>
              <a
                href="#latest"
                className="rounded-md border border-[var(--brand-line)] bg-white/70 px-4 py-2.5 text-sm text-[var(--brand-ink)] backdrop-blur transition hover:bg-white"
              >
                최신 글 보기
              </a>
            </div>
          </div>
        </section>

        <section id="latest" className="mx-auto max-w-5xl px-5 pb-20 md:px-8">
          <div className="mb-6 flex items-end justify-between gap-4">
            <div>
              <h2 className="font-[family-name:var(--font-display)] text-3xl text-[var(--brand-ink)]">최신 글</h2>
              <p className="mt-1 text-sm text-[var(--brand-ink-soft)]">자체 사이트에 발행된 글만 표시됩니다.</p>
            </div>
          </div>

          <AdSenseSlot slot="home-top" />

          {error ? (
            <p className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              API 연결 실패: {error}
            </p>
          ) : null}

          {!error && posts.length === 0 ? (
            <div className="rounded-md border border-dashed border-[var(--brand-line)] bg-white/70 px-5 py-12 text-center">
              <p className="font-[family-name:var(--font-display)] text-2xl text-[var(--brand-ink)]">아직 공개된 글이 없습니다</p>
              <p className="mx-auto mt-2 max-w-md text-sm text-[var(--brand-ink-soft)]">
                운영 화면에서 카테고리를 고르고 주제를 생성한 뒤 즉시 발행하면 이 공간에 쌓입니다.
              </p>
              <Link
                href="/admin/generate"
                className="mt-5 inline-flex rounded-md bg-[var(--brand-teal)] px-4 py-2 text-sm font-medium text-white"
              >
                첫 글 생성하기
              </Link>
            </div>
          ) : (
            <ul className="divide-y divide-[var(--brand-line)] border-y border-[var(--brand-line)]">
              {posts.map((post, i) => (
                <li key={post.id} className="animate-rise py-6" style={{ animationDelay: `${i * 60}ms` }}>
                  <Link href={`/posts/${post.slug}`} className="group block">
                    <div className="flex flex-wrap items-center gap-2 text-xs tracking-wide text-[var(--brand-ink-soft)] uppercase">
                      <span>{post.category_name || "카테고리"}</span>
                      {post.published_at ? (
                        <time dateTime={post.published_at}>
                          {new Date(post.published_at).toLocaleString("ko-KR")}
                        </time>
                      ) : null}
                    </div>
                    <h3 className="mt-2 font-[family-name:var(--font-display)] text-2xl text-[var(--brand-ink)] transition-colors group-hover:text-[var(--brand-teal)]">
                      {post.title}
                    </h3>
                    <p className="mt-2 max-w-3xl text-[var(--brand-ink-soft)]">{post.excerpt}</p>
                  </Link>
                </li>
              ))}
            </ul>
          )}

          <AdSenseSlot slot="home-bottom" label="하단 광고 자리표시자" />
        </section>
      </main>
    </div>
  );
}
