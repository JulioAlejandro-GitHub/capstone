import { useLayoutEffect, useState, type RefObject } from 'react';

export type ControlBarMenuAnchor = { top: number; right: number };

/**
 * Shared anchoring and dismissal for every popover of the unified immersive
 * control bar. Generalized verbatim from the gallery filter dropdown so the
 * three functional groups ("Controles de imagen", "Imagen", "Estado de
 * detección") share one implementation instead of three copies:
 *
 * - the menu is portaled to document.body and positioned `fixed`, so no
 *   ancestor `overflow: hidden` or `backdrop-filter` can clip it;
 * - it is pinned to the trigger's right edge (never overflows the right border
 *   of the canvas) and the offset is clamped so a trigger close to the left
 *   edge flips the menu rightwards instead of pushing it off screen;
 * - a document-level `mousedown` closes it when the click lands outside both
 *   the trigger and the menu;
 * - Escape closes it and returns focus to the trigger.
 *
 * `width` must match the menu's CSS width: the node is not measured because it
 * only mounts once an anchor exists.
 */
export function useControlBarMenu({
  open,
  triggerRef,
  menuRef,
  onClose,
  width = 280,
}: {
  open: boolean;
  triggerRef: RefObject<HTMLButtonElement | null>;
  menuRef: RefObject<HTMLDivElement | null>;
  onClose: () => void;
  width?: number;
}): ControlBarMenuAnchor | null {
  const [anchor, setAnchor] = useState<ControlBarMenuAnchor | null>(null);

  // Layout effect: the anchor must exist before paint so a keyboard-opened
  // menu can move focus into its first option in the very next frame.
  useLayoutEffect(() => {
    if (!open) {
      setAnchor(null);
      return;
    }
    const reposition = () => {
      const rect = triggerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const right = Math.max(
        12,
        Math.min(window.innerWidth - rect.right, window.innerWidth - width - 12),
      );
      setAnchor({ top: rect.bottom + 6, right });
    };
    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (triggerRef.current?.contains(target)) return;
      if (menuRef.current?.contains(target)) return;
      onClose();
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.stopPropagation();
      onClose();
      triggerRef.current?.focus();
    };
    reposition();
    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('resize', reposition);
    window.addEventListener('scroll', reposition, true);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('resize', reposition);
      window.removeEventListener('scroll', reposition, true);
    };
  }, [menuRef, onClose, open, triggerRef, width]);

  return anchor;
}
