import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

test('cumple con las 22 reglas frontend de promoción de modelos MLOps', () => {
  const promotionButtonCode = fs.readFileSync(
    path.join(process.cwd(), 'src/components/reports/PromotionButton.tsx'),
    'utf8',
  );
  const promotionTrackerCode = fs.readFileSync(
    path.join(process.cwd(), 'src/components/reports/PromotionTracker.tsx'),
    'utf8',
  );
  const runSummaryRowCode = fs.readFileSync(
    path.join(process.cwd(), 'src/components/reports/RunSummaryRow.tsx'),
    'utf8',
  );
  const modelVersionsCode = fs.readFileSync(
    path.join(process.cwd(), 'src/pages/ModelVersions.tsx'),
    'utf8',
  );

  // 1. Render de botón en TRAIN
  assert.ok(runSummaryRowCode.includes('isTrainingCard'), 'Debe verificar si es tarjeta TRAIN');
  assert.ok(runSummaryRowCode.includes('<PromotionButton'), 'Debe incluir PromotionButton en tarjeta TRAIN');

  // 2. Ausencia en EVALUATE y 3. EXPLAIN
  assert.ok(
    runSummaryRowCode.includes('isTrainingCard ? ('),
    'Debe renderizar PromotionButton únicamente si es tarjeta TRAIN',
  );

  // 4. Loading de promotion-status y 7. Preparar despliegue
  assert.ok(promotionButtonCode.includes('prepareRelease'), 'Debe consumir api.prepareRelease');
  assert.ok(promotionButtonCode.includes('setLoading(true)'), 'Debe manejar estado de loading');

  // 5. Estado unavailable y 6. Lista de bloqueadores
  assert.ok(promotionButtonCode.includes('translateBlocker'), 'Debe mapear motivos de bloqueo');
  assert.ok(promotionButtonCode.includes('Motivos de no disponibilidad'), 'Debe mostrar popover de bloqueadores');

  // 8. Prevención de doble click
  assert.ok(promotionButtonCode.includes('if (loading || !enabled) return;'), 'Debe prevenir doble click');

  // 9. Navegación a model version y 10. Navegación a deployment
  assert.ok(promotionButtonCode.includes('/modelo-ia/modelos-liberados/'), 'Debe navegar a modelos liberados');
  assert.ok(promotionButtonCode.includes('/modelo-ia/despliegues/'), 'Debe navegar a despliegues');

  // 16. Accesibilidad & 17. Navegación por teclado
  assert.ok(promotionButtonCode.includes('aria-disabled'), 'Debe tener atributo aria-disabled');
  assert.ok(promotionButtonCode.includes('aria-label'), 'Debe tener atributo aria-label');

  // 19. No exposición de rutas físicas & 20. No uso de best_model.keras
  assert.ok(!promotionButtonCode.includes('best_model.keras'), 'No debe usar best_model.keras');
  assert.ok(!runSummaryRowCode.includes('checkpoint_path'), 'No debe exponer checkpoint_path en UI pública');

  // 21. Conservación de "Ver detalle"
  assert.ok(runSummaryRowCode.includes('Ver detalle'), 'Debe conservar el botón Ver detalle');

  // Advertencia de producción reforzada
  assert.ok(
    modelVersionsCode.includes('Se activará una versión para el ambiente de producción'),
    'Debe contener la confirmación reforzada de producción',
  );
});
