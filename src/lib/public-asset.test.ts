import { afterEach, describe, expect, it, vi } from 'vitest';
import { getPublicAssetPath } from './public-asset';

describe('getPublicAssetPath', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('returns a root-relative path in development', () => {
    vi.stubEnv('NODE_ENV', 'development');
    vi.stubEnv('NEXT_PUBLIC_BASE_PATH', '');

    expect(getPublicAssetPath('/logo.png')).toBe('/logo.png');
  });

  it('prefixes the production basePath for static assets', () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('NEXT_PUBLIC_BASE_PATH', '');

    expect(getPublicAssetPath('/logo.png')).toBe('/qualtio-tech-radar/logo.png');
  });

  it('uses an explicit public basePath when provided', () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('NEXT_PUBLIC_BASE_PATH', '/custom-base');

    expect(getPublicAssetPath('logo.png')).toBe('/custom-base/logo.png');
  });
});
