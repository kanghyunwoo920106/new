"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/admin", label: "대시보드" },
  { href: "/admin/generate", label: "생성·예약" },
  { href: "/admin/posts", label: "글" },
  { href: "/admin/jobs", label: "발행 큐" },
];

export function AdminNav() {
  const pathname = usePathname();
  return (
    <nav className="flex flex-wrap gap-2">
      {links.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
              active
                ? "bg-[var(--brand-teal)] text-white"
                : "bg-white/70 text-[var(--brand-ink-soft)] hover:bg-white hover:text-[var(--brand-ink)]"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
      <Link
        href="/"
        className="rounded-md px-3 py-1.5 text-sm text-[var(--brand-ink-soft)] hover:text-[var(--brand-ink)]"
      >
        공개 사이트 →
      </Link>
    </nav>
  );
}
