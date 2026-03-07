'use client';

interface SourceCoverageBadgeProps {
  coverage?: number;
  githubOnly?: boolean;
}

export function SourceCoverageBadge({ coverage, githubOnly }: SourceCoverageBadgeProps) {
  if (!coverage || coverage <= 0) {
    return null;
  }

  const toneClass = githubOnly
    ? 'border-amber-500/40 bg-amber-500/10 text-amber-300'
    : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300';

  return (
    <span className={`inline-flex rounded border px-1.5 py-0.5 text-[11px] ${toneClass}`}>
      {githubOnly ? 'GitHub only' : `${coverage} sources`}
    </span>
  );
}
