import { describe, expect, it, vi } from 'vitest';
import { focusShortcutTarget, type ShortcutTarget } from './search-shortcut';

function makeTarget(visible: boolean) {
  const focus = vi.fn();
  const target: ShortcutTarget = {
    focus,
    offsetParent: visible ? ({} as Element) : null,
  };

  return { target, focus };
}

describe('focusShortcutTarget', () => {
  it('focuses visible targets', () => {
    const { target, focus } = makeTarget(true);

    expect(focusShortcutTarget(target)).toBe(true);
    expect(focus).toHaveBeenCalledTimes(1);
  });

  it('ignores hidden targets', () => {
    const { target, focus } = makeTarget(false);

    expect(focusShortcutTarget(target)).toBe(false);
    expect(focus).not.toHaveBeenCalled();
  });

  it('ignores missing targets', () => {
    expect(focusShortcutTarget(null)).toBe(false);
  });
});
