import { AdminNav } from "@/components/admin-nav";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <div className="border-b border-[var(--brand-line)]/70 bg-white/40 backdrop-blur-sm">
        <div className="mx-auto max-w-5xl px-5 py-6 md:px-8">
          <p className="font-[family-name:var(--font-display)] text-3xl tracking-tight text-[var(--brand-ink)]">
            루멘포스트 운영
          </p>
          <p className="mt-1 max-w-2xl text-sm text-[var(--brand-ink-soft)]">
            Phase 1 · 자체 사이트 자동 발행 · sequential_cycle · 비민감 카테고리 allowlist · AdSense placeholder
          </p>
          <div className="mt-4">
            <AdminNav />
          </div>
        </div>
      </div>
      <div className="mx-auto max-w-5xl px-5 py-8 md:px-8">{children}</div>
    </div>
  );
}
