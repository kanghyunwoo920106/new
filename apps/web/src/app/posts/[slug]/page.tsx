import Link from "next/link";
import { notFound } from "next/navigation";
import { AdSenseSlot } from "@/components/adsense-slot";
import { SiteHeader } from "@/components/site-header";
import { api } from "@/lib/api";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props) {
  const { slug } = await params;
  try {
    const post = await api.publicPost(slug);
    return {
      title: post.title,
      description: post.excerpt,
      keywords: post.seo_tags.map((t) => t.tag),
    };
  } catch {
    return { title: "글을 찾을 수 없습니다" };
  }
}

export default async function PostPage({ params }: Props) {
  const { slug } = await params;
  let post;
  try {
    post = await api.publicPost(slug);
  } catch {
    notFound();
  }

  return (
    <div className="min-h-screen">
      <SiteHeader />
      <article className="mx-auto max-w-3xl px-5 py-10 md:px-8">
        <Link href="/" className="text-sm text-[var(--brand-ink-soft)] hover:text-[var(--brand-teal)]">
          ← 루멘포스트
        </Link>
        <p className="mt-6 text-xs tracking-[0.18em] text-[var(--brand-ink-soft)] uppercase">
          {post.category_name}
          {post.published_at ? ` · ${new Date(post.published_at).toLocaleString("ko-KR")}` : ""}
        </p>
        <h1 className="animate-ink mt-3 font-[family-name:var(--font-display)] text-4xl leading-tight text-[var(--brand-ink)] md:text-5xl">
          {post.title}
        </h1>
        <p className="mt-4 text-lg text-[var(--brand-ink-soft)]">{post.excerpt}</p>
        {post.seo_tags.length > 0 ? (
          <ul className="mt-5 flex flex-wrap gap-2">
            {post.seo_tags.map((t) => (
              <li
                key={t.tag}
                className="rounded-sm bg-white/70 px-2 py-1 text-xs text-[var(--brand-ink-soft)]"
              >
                #{t.tag}
              </li>
            ))}
          </ul>
        ) : null}

        <AdSenseSlot slot="article-top" />

        <div
          className="prose-post animate-rise mt-2"
          dangerouslySetInnerHTML={{ __html: post.body_html || "" }}
        />

        <AdSenseSlot slot="article-bottom" label="본문 하단 광고 자리표시자" />
      </article>
    </div>
  );
}
