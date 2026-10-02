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
        <span className="ds-status" data-tone={tone}>
            <span aria-hidden="true">{ICON[tone]}</span>
            {label ?? status ?? 'unknown'}
        </span>
    );
}