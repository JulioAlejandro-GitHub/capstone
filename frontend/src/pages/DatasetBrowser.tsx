import { useEffect, useMemo, useState } from 'react';

import { Loading } from '../components/Loading';
import { api } from '../services/api';
import type { DatasetBrowserSummary, DatasetImagePage } from '../types/api';

interface DatasetBrowserProps {
  datasource: string;
}

type DatasetTab = 'description' | 'split' | 'train' | 'val' | 'test';

const tabs: Array<{ key: DatasetTab; label: string }> = [
  { key: 'description', label: 'Descripción' },
  { key: 'split', label: 'Split físico' },
  { key: 'train', label: 'Entrenamiento' },
  { key: 'val', label: 'Validación' },
  { key: 'test', label: 'Prueba' },
];

const pageSizeOptions = [12, 24, 48, 96];

function percent(value: number | null | undefined) {
  if (value === null || value === undefined) return '-';
  return `${Math.round(Number(value) * 100)} %`;
}

function bytes(value: number | null | undefined) {
  if (!value) return '-';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function DatasetBrowser({ datasource }: DatasetBrowserProps) {
  const [summary, setSummary] = useState<DatasetBrowserSummary | null>(null);
  const [images, setImages] = useState<DatasetImagePage | null>(null);
  const [tab, setTab] = useState<DatasetTab>('description');
  const [className, setClassName] = useState('all');
  const [pageSize, setPageSize] = useState(24);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const imageSplit = useMemo(() => (['train', 'val', 'test'].includes(tab) ? tab : null), [tab]);

  useEffect(() => {
    setError(null);
    api
      .getDatasetSummary(datasource)
      .then(setSummary)
      .catch((err: Error) => setError(err.message));
  }, [datasource]);

  useEffect(() => {
    setPage(1);
  }, [datasource, tab, className, pageSize]);

  useEffect(() => {
    if (!imageSplit) {
      setImages(null);
      return;
    }
    setError(null);
    api
      .getDatasetImages(datasource, {
        split: imageSplit,
        class_name: className,
        page,
        page_size: pageSize,
      })
      .then(setImages)
      .catch((err: Error) => setError(err.message));
  }, [datasource, imageSplit, className, page, pageSize]);

  if (error) return <section className="panel error">{error}</section>;
  if (!summary) return <Loading />;

  return (
    <section className="page">
      <div className="page-title">
        <div>
          <h1>Dataset de Malaria</h1>
          <p>{summary.dataset.description}</p>
        </div>
        <span className="domain-badge">Dataset</span>
      </div>

      <div className="tabs">
        {tabs.map((item) => (
          <button
            key={item.key}
            className={tab === item.key ? 'active' : ''}
            onClick={() => setTab(item.key)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'description' ? (
        <>
          <section className="dataset-info-grid">
            <div className="panel">
              <h2>Fuente original</h2>
              <p>
                Este proyecto utiliza el dataset Malaria disponible en TensorFlow Datasets,
                compuesto por imágenes microscópicas de células sanguíneas clasificadas en
                dos categorías: células no infectadas y células parasitadas.
              </p>
              <div className="dataset-links">
                <a href={summary.dataset.source_url} target="_blank" rel="noreferrer">
                  TensorFlow Datasets - Malaria
                </a>
                {summary.dataset.nih_nlm_url ? (
                  <a href={summary.dataset.nih_nlm_url} target="_blank" rel="noreferrer">
                    Fuente NIH/NLM
                  </a>
                ) : null}
              </div>
              <p className="muted-text">El dataset original no se modifica directamente.</p>
            </div>

            <div className="panel">
              <h2>Convención de etiquetas</h2>
              <div className="dataset-facts">
                <span>0 = {summary.label_mapping['0']}</span>
                <span>1 = {summary.label_mapping['1']}</span>
                <span>Clase positiva clínica = {summary.label_mapping.positive_class}</span>
                <span>raw_model_score = {summary.label_mapping.raw_model_score_meaning}</span>
              </div>
            </div>
          </section>

          <section className="panel">
            <h2>Proceso de split físico</h2>
            <p>
              Se descarga o lee el dataset original desde TensorFlow Datasets, se aplica la
              convención clínica del proyecto y se realiza una división física reproducible y
              estratificada. Las imágenes se guardan en carpetas locales separadas por split y
              clase, y todos los modelos usan los mismos subconjuntos.
            </p>
            <p>
              El split físico fue creado para evitar que cada entrenamiento genere una división
              aleatoria diferente. Esto permite comparar custom_cnn, VGG16, SVM, TTA, ensemble y
              futuros modelos de manera justa y reproducible.
            </p>
          </section>
        </>
      ) : null}

      {tab === 'split' ? (
        <>
          <section className="metrics-grid">
            <div className="metric-card">
              <span>Entrenamiento</span>
              <strong>{percent(summary.split_process.train_ratio)}</strong>
            </div>
            <div className="metric-card">
              <span>Validación</span>
              <strong>{percent(summary.split_process.val_ratio)}</strong>
            </div>
            <div className="metric-card">
              <span>Prueba</span>
              <strong>{percent(summary.split_process.test_ratio)}</strong>
            </div>
            <div className="metric-card">
              <span>Seed</span>
              <strong>{summary.split_process.seed}</strong>
            </div>
          </section>

          <section className="panel">
            <h2>Distribución oficial</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Split</th>
                    <th>Uninfected</th>
                    <th>Parasitized</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.split_table.map((row) => (
                    <tr key={row.split_name}>
                      <td>{row.display_name}</td>
                      <td>{row.uninfected}</td>
                      <td>{row.parasitized}</td>
                      <td>{row.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel clinical-disclaimer">
            <strong>¿Por qué no usar split aleatorio en cada entrenamiento?</strong>
            <p>
              Un split aleatorio dinámico puede hacer que cada modelo vea imágenes distintas
              durante entrenamiento, validación o prueba. Eso dificulta comparar métricas entre
              modelos. El split físico deja los subconjuntos fijos y auditables.
            </p>
            <p>El conjunto de prueba debe mantenerse fijo y no debe usarse para ajustar hiperparámetros.</p>
          </section>
        </>
      ) : null}

      {imageSplit ? (
        <>
          <section className="panel">
            <div className="section-heading">
              <h2>Imágenes de {tabs.find((item) => item.key === tab)?.label}</h2>
              <span>{images ? `${images.total_items} imágenes encontradas` : 'Cargando imágenes'}</span>
            </div>
            <div className="filters-grid">
              <label>
                Clase
                <select value={className} onChange={(event) => setClassName(event.target.value)}>
                  <option value="all">Todas</option>
                  <option value="uninfected">Uninfected</option>
                  <option value="parasitized">Parasitized</option>
                </select>
              </label>
              <label>
                Tamaño de página
                <select
                  value={pageSize}
                  onChange={(event) => setPageSize(Number(event.target.value))}
                >
                  {pageSizeOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </section>

          {!images ? <Loading /> : null}
          {images ? (
            <>
              <div className="dataset-image-grid">
                {images.items.map((item) => (
                  <article className="dataset-image-card" key={item.image_id}>
                    <img src={api.datasetImageUrl(item.image_id, datasource)} alt={item.filename} />
                    <strong>{item.filename}</strong>
                    <span>Split: {item.split_name}</span>
                    <span>Clase: {item.class_name}</span>
                    <span>Índice: {item.class_index}</span>
                    <span>
                      Dimensiones:{' '}
                      {item.image_width && item.image_height
                        ? `${item.image_width} x ${item.image_height}`
                        : '-'}
                    </span>
                    <span>Tamaño: {bytes(item.file_size_bytes)}</span>
                  </article>
                ))}
              </div>
              <div className="pagination-bar">
                <button
                  type="button"
                  disabled={images.page <= 1}
                  onClick={() => setPage((value) => Math.max(1, value - 1))}
                >
                  Anterior
                </button>
                <span>
                  Página {images.page} de {images.total_pages}
                </span>
                <button
                  type="button"
                  disabled={images.page >= images.total_pages}
                  onClick={() => setPage((value) => Math.min(images.total_pages, value + 1))}
                >
                  Siguiente
                </button>
              </div>
            </>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
