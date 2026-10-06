import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="relative z-10 mx-auto flex w-full max-w-5xl items-center justify-between px-5 py-5 md:px-8">
      <Link href="/" className="group flex items-baseline gap-2">
        <span className="font-[family-name:var(--font-display)] text-2xl tracking-tight text-[var(--brand-ink)] transition-colors group-hover:text-[var(--brand-teal)] md:text-3xl">
          루멘포스트
        </span>
        <span className="hidden text-xs tracking-[0.2em] text-[var(--brand-ink-soft)] uppercase sm:inline">
          LumenPost
        </span>
      </Link>
      <nav className="flex items-center gap-4 text-sm text-[var(--brand-ink-soft)]">
        <Link href="/" className="transition-colors hover:text-[var(--brand-ink)]">
          블로그
        </Link>
        <Link
          href="/admin"
          className="rounded-md bg-[var(--brand-teal)] px-3 py-1.5 font-medium text-white transition-transform hover:-translate-y-0.5"
        >
          운영
        </Link>
      </nav>
    </header>
  );
}
