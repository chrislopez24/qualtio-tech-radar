const DEFAULT_PRODUCTION_BASE_PATH = '/qualtio-tech-radar';

function normalizePath(path: string): string {
  return path.startsWith('/') ? path : `/${path}`;
}

export function getPublicAssetPath(path: string): string {
  const normalizedPath = normalizePath(path);
  const configuredBasePath =
    process.env.NEXT_PUBLIC_BASE_PATH ||
    (process.env.NODE_ENV === 'production' ? DEFAULT_PRODUCTION_BASE_PATH : '');

  return `${configuredBasePath}${normalizedPath}`;
}
