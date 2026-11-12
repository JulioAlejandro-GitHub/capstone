import React from 'react';

type Tone = 'approved' | 'warning' | 'rejected' | 'blocked' | 'running' | 'neutral';

const TONE: Record<string, Tone> = {
    COMPLETED: 'approved',
    completed: 'approved',
    PASS: 'approved',
    approved: 'approved',
    FROZEN: 'blocked',
    frozen: 'blocked',
    FAILED: 'rejected',
    failed: 'rejected',
    FAIL: 'rejected',
    rejected: 'rejected',
    STARTED: 'running',
    started: 'running',
    RUNNING: 'running',
    warning: 'warning',
    PENDING: 'warning',
    pending: 'warning',
};

/* Traducción de .ds-status[data-tone=…] (ds-primitives.css + tokens.css) */
const TONE_CLASS: Record<Tone, string> = {
    approved: 'bg-ok-soft text-ok',
    warning: 'bg-warn-soft text-warn',
    rejected: 'bg-danger-soft text-danger',
    blocked: 'bg-blocked-soft text-blocked',
    running: 'bg-accent-soft text-accent',
    neutral: 'bg-neutral-soft text-neutral-fg',
};

const ICON: Record<Tone, string> = {
    approved: '✓',
    warning: '⚠',
    rejected: '✗',
    blocked: '🔒',
    running: '●',
    neutral: '·',
};

export function StatusPill({ status, label }: { status?: string | null; label?: string }) {
    const tone = TONE[status ?? ''] ?? 'neutral';
    return (
        <span className={`inline-flex items-center gap-1 rounded-pill px-2 py-0.5 text-xs font-semibold ${TONE_CLASS[tone]}`}>
            <span aria-hidden="true">{ICON[tone]}</span>
            {label ?? status ?? 'unknown'}
        </span>
    );
}
