import type { Technology, AITechnology } from './types';

export function matchesTechnologySearch(
  technology: Technology | AITechnology,
  rawQuery: string,
): boolean {
  const query = rawQuery.trim().toLowerCase();
  if (!query) {
    return true;
  }

  const description = technology.description?.toLowerCase() ?? '';
  const extendedFields = [
    'whyNow' in technology ? technology.whyNow : '',
    'owner' in technology ? technology.owner : '',
    'useCases' in technology ? technology.useCases?.join(' ') : '',
    'alternatives' in technology ? technology.alternatives?.join(' ') : '',
    'evidence' in technology
      ? technology.evidence
          ?.map((item) => (typeof item === 'string' ? item : Object.values(item).join(' ')))
          .join(' ')
      : '',
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  return (
    technology.name.toLowerCase().includes(query) ||
    description.includes(query) ||
    extendedFields.includes(query) ||
    technology.quadrant.includes(query) ||
    technology.ring.includes(query)
  );
}
