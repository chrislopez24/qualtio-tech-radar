export interface ShortcutTarget {
  focus: () => void;
  offsetParent: Element | null;
}

export function focusShortcutTarget(target: ShortcutTarget | null): boolean {
  if (!target || target.offsetParent === null) {
    return false;
  }

  target.focus();
  return true;
}
