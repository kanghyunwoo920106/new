type Props = {
  slot?: string;
  label?: string;
};

/** AdSense not approved yet — visual placeholder only. */
export function AdSenseSlot({ slot = "placeholder", label = "광고 영역 (승인 전 자리표시자)" }: Props) {
  return (
    <aside
      aria-label={label}
      data-adsense-slot={slot}
      className="my-8 flex min-h-28 items-center justify-center rounded-sm border border-dashed border-[var(--brand-line)] bg-[color-mix(in_oklab,var(--brand-mist)_70%,transparent)] px-4 py-6 text-center"
    >
      <div>
        <p className="text-xs font-medium tracking-[0.18em] text-[var(--brand-ink-soft)] uppercase">
          AdSense placeholder
        </p>
        <p className="mt-1 text-sm text-[var(--brand-ink-soft)]">{label}</p>
      </div>
    </aside>
  );
}
