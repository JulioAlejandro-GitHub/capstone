import type { ArchitectureBlock, ModelArchitecture } from '../../types/modelArchitecture';
import { blockOperations, tensorPath } from './mathOperations';

export function MathFunctionPanel({ data, block, onBlock }: { data: ModelArchitecture; block: ArchitectureBlock; onBlock: (id: string) => void }) {
  const operations = blockOperations(data, block);
  return <section className="report-section mx-math" aria-label="Función matemática">
    <div className="ds-page-header"><h3>Función matemática · {block.label}</h3>
      <label className="mx-filter">Bloque<select className="ds-control" value={block.id} onChange={event => onBlock(event.target.value)}>
        {data.blocks.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
      </select></label></div>
    <p className="mx-path" aria-label="Recorrido del tensor">{tensorPath(data).map((step, index) => <span key={`${step}-${index}`}>{step}</span>)}</p>
    {operations.length ? <ol className="mx-operations">{operations.map(operation => <li key={operation.id}>
      <div><strong>{operation.title}{operation.count > 1 ? ` · ${operation.count} capas` : ''}</strong>
        {operation.origin === 'reference' && <span className="scc-meta"> · Referencia</span>}<small>{operation.detail}</small></div>
      {operation.formula}
    </li>)}</ol> : <p>Este bloque no aplica una operación con pesos o función propia.</p>}
    <p className="scc-meta">Las fórmulas describen la operación registrada del modelo, no el cálculo de una imagen. Los valores por muestra requieren guardar activaciones.</p>
  </section>;
}
