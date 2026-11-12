/* HARNESES DE DESARROLLO (no forma parte de la migración): permite ver en el navegador
   el tema Tailwind de frontend2 y los componentes ya convertidos, sin tocar el
   frontend original ni los contenedores. Borrar cuando App.tsx quede operativo. */
import React from 'react';
import ReactDOM from 'react-dom/client';

import './styles.css';
import { DomainBadge } from './components/DomainBadge';
import { Loading } from './components/Loading';
import { MetricCard } from './components/MetricCard';
import { StatusBadge } from './components/StatusBadge';
import { StatusPill } from './components/ui/StatusPill';
import { ComparisonEligibilityStatus } from './components/reports/ComparisonEligibilityStatus';
import { MetricChip } from './components/reports/MetricChip';
import { ReportBadge } from './components/reports/ReportBadge';
import { RunProcessBadge } from './components/reports/RunProcessBadge';
import { ScientificParameters } from './components/reports/ScientificParameters';
import { ProductionStepIndicator } from './components/deployments/ProductionStepIndicator';

const readiness = { current_step: 3, production_status: { available_for_inference: false } } as any;
const parameters = { target_recall: 0.9, min_recall: 0.85, calibrate_threshold: true, threshold: 0.62,
  early_stopping_patience: 8, early_stopping_min_delta: 0.001, min_class_fraction: 0.15,
  reject_prediction_collapse: true, val_f2_parasitized: 0.91 } as any;
const eligibility = { eligible: true, train: true, evaluate: true, explain: null, reasons: [] } as any;

function Surface({ surface }: { surface: 'workbench' | 'lab' }) {
  return (
    <section data-surface={surface} className="rounded-panel border border-border bg-surface p-5 grid gap-4">
      <h2 className="m-0 text-fg-strong text-lg font-bold">{surface === 'workbench' ? 'Superficie workbench (clara)' : 'Superficie lab (oscura)'}</h2>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(160px,1fr))] gap-3">
        <MetricCard label="Precisión" value={0.94} hint="validation" />
        <MetricCard label="Células revisadas" value={128} />
        <div className="grid gap-1 rounded-panel border border-border bg-surface p-4 shadow-panel">
          <div className="flex flex-wrap gap-2">
            <StatusBadge status="completed" /><StatusBadge status="failed" /><StatusBadge status="started" /><StatusBadge status="unknown" />
            <DomainBadge domain="Parasitos" />
            <StatusPill status="PASS" /><StatusPill status="PENDING" /><StatusPill status="FROZEN" /><StatusPill status="RUNNING" />
            <ReportBadge level="success">ok</ReportBadge><ReportBadge level="warning">revisar</ReportBadge><ReportBadge level="danger">falló</ReportBadge>
            <RunProcessBadge kind="training" /><RunProcessBadge kind="evaluation" /><RunProcessBadge kind="explainability" />
            <ComparisonEligibilityStatus eligibility={eligibility} />
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            <MetricChip label="F1" value={0.87} /><MetricChip label="Recall" value={0.93} /><MetricChip label="Especificidad" value={0.98} />
          </div>
        </div>
        <ScientificParameters parameters={parameters} />
      </div>
      <ProductionStepIndicator readiness={readiness} />
      <Loading />
    </section>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <main className="min-h-screen bg-canvas p-7 grid gap-6 max-w-[1100px] margin-0-auto">
      <header className="grid gap-1">
        <h1 className="m-0 text-ink-strong text-2xl font-bold">frontend2 — vista previa de la migración a Tailwind</h1>
        <p className="m-0 text-muted text-sm">18 de 124 componentes migrados. Se muestra el sistema de diseño (tokens, radios, sombras, superficies) y los componentes ya convertidos.</p>
      </header>
      <Surface surface="workbench" />
      <Surface surface="lab" />
    </main>
  </React.StrictMode>,
);
