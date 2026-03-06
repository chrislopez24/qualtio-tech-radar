import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

function readRepoFile(pathSegments: string[]): string {
  return readFileSync(join(process.cwd(), ...pathSegments), 'utf8');
}

function collectFiles(pathSegments: string[]): string[] {
  const root = join(process.cwd(), ...pathSegments);
  const entries = readdirSync(root, { withFileTypes: true });
  const files: string[] = [];

  for (const entry of entries) {
    const fullPath = join(root, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectFiles([...pathSegments, entry.name]));
      continue;
    }

    if (entry.isFile()) {
      files.push(fullPath);
    }
  }

  return files;
}

describe('repo contract: shadcn CLI is not part of the workflow', () => {
  it('does not keep shadcn in package metadata, CSS imports, source imports, docs, or CLI config', () => {
    const packageJson = JSON.parse(readRepoFile(['package.json'])) as {
      devDependencies?: Record<string, string>;
    };

    expect(packageJson.devDependencies?.shadcn).toBeUndefined();

    const globalCss = readRepoFile(['src', 'app', 'globals.css']);
    expect(globalCss).not.toContain('@import "shadcn/tailwind.css"');

    const sourceFiles = collectFiles(['src']).filter(
      (file) => /\.(css|ts|tsx)$/.test(file) && !/\.test\.(ts|tsx)$/.test(file),
    );

    for (const file of sourceFiles) {
      const contents = readFileSync(file, 'utf8');
      expect(contents).not.toMatch(/from\s+["']shadcn["']/);
      expect(contents).not.toMatch(/import\s+["']shadcn\/tailwind\.css["']/);
    }

    const readme = readRepoFile(['README.md']);
    expect(readme).not.toContain('shadcn/ui');
    expect(readme).not.toContain('shadcn CLI');

    expect(existsSync(join(process.cwd(), 'components.json'))).toBe(false);
  });
});
