Diagnóstico read-only completado. No se modificaron archivos, código, Compose, contenedores, volúmenes ni base de datos; el árbol Git permanece limpio.
1. Estado Alembic
Comprobación	Resultado
Head del repositorio	20260812_02
Current en PostgreSQL, consultado con SELECT	20260812_02
Cadena Alembic	19 revisiones, lineal y sin branches
docker compose exec backend python -m alembic current	Falla, exit 255
docker compose exec backend python -m alembic heads	Falla, exit 255


Ambos comandos fallan con:
FAILED: No 'script_location' key found in configuration.
El repositorio y la base coinciden en 20260812_02, pero los comandos Alembic dentro del backend no pudieron confirmarlo de forma independiente debido a los mounts.
Además coexisten dos trackers:
- alembic_version;
- schema_migrations, con 23 migraciones SQL legacy registradas hasta 029_stage2_model_publications.sql.
Esto introduce riesgo de doble autoridad y deriva.
2. Estado de Docker y mounts
docker compose config terminó correctamente. docker compose ps muestra backend, PostgreSQL y frontend activos; PostgreSQL está saludable.
Mounts efectivos relevantes:
Destino	Origen lógico	Modo	Consecuencia
/app del backend	./backend_api	RW	Oculta lo copiado a /app durante el build
Proyecto ML	./malaria_dl_local_project	RO	Código ML visible
releases	subdirectorio específico	RW	Excepción de escritura para artefactos publicados
Dataset-split src	bind específico	RO	Biblioteca compartida visible
Datos PostgreSQL	volumen nombrado	RW	Persistencia correcta


backend_api/Dockerfile:43-44 copia alembic/ y alembic.ini a /app, pero docker-compose.override.yml:5-6 monta backend_api/ encima. Ese directorio no contiene esos dos elementos.
Cambio mínimo futuro:
- ./alembic:/app/alembic:ro
- ./alembic.ini:/app/alembic.ini:ro
Después se debe recrear únicamente el backend.
El volumen lógico postgres_data aparece en Docker como capstone-malaria_postgres_data por el nombre del proyecto Compose.
También se detectó deriva entre la configuración actual del rol PostgreSQL del servicio db y el cluster ya inicializado en el volumen: el acceso directo con el rol declarado actualmente falla, mientras que la conexión operativa del backend funciona. No se corrigió ni se expusieron credenciales.
Configuración de conexión:
- Compose inyecta DATABASE_URL usando db:5432.
- backend_api/app/config.py:93-110 exige esa variable.
- backend_api/app/db.py:40-47 crea el engine.
- alembic/env.py:6-12 usa la misma configuración.
- El tracker ML también prioriza DATABASE_URL; conserva un fallback exclusivamente local que no se usa en Docker.
3. Escritores de TRAIN, EVALUATE y linaje
Acción	Punto canónico
INSERT genérico de run	persistence/run_repository.py:340-435, start_run()
Wrapper de creación	persistence/tracking.py:503-674, start_tracking_run()
Crear TRAIN	training/trainer.py:1321-1395
Crear EVALUATE	evaluation/evaluator.py:244-273
Marcar cualquier run completed	run_repository.py:537-622, finish_run()
Cerrar TRAIN	trainer.py:2449-2546
Cerrar EVALUATE	evaluator.py:402-414
Crear linaje EVALUATE→TRAIN	evaluator.py:80-186, track_source_training_lineage()
INSERT efectivo de linaje	persistence/lineage.py:547-585, _insert_run_lineage()
Linaje + metadata en una transacción	lineage.py:679-722, create_run_lineage_with_metadata()
Backfill alternativo de linaje	scripts/backfill_run_lineage.py:270-301, sólo con --apply
Crear model version inicial	trainer.py:2168-2198
Finalizar model version gobernada	training_model_version_finalizer.py:67-264


Otros puntos:
- scripts/test_db.py:79-98,337 crea y completa un TRAIN técnico.
- run_train_all_models.py y run_evaluate_all_trainings.py sólo orquestan los entrypoints canónicos.
- No existe un endpoint backend que cree TRAIN o EVALUATE.
- El segundo INSERT INTO runs productivo, en governance/repository.py, crea únicamente runs de inferencia.
El orquestador de evaluaciones exige --require-lineage. El CLI directo no: sin esa opción, un fallo al guardar linaje puede terminar como advertencia y el EVALUATE aún podría quedar completed.
4. Orden real de persistencia
Cada operación habitual abre su propia transacción mediante engine.begin() en persistence/database.py:49-54.
TRAIN:
1. INSERT con status='started'; commit.
2. Progreso e historial; múltiples commits.
3. Escritura de artefactos en filesystem.
4. Métricas y reportes; commits independientes.
5. Registro de artefactos; normalmente un commit por archivo.
6. Registro de imágenes utilizadas.
7. INSERT de model_versions como discovered; commit.
8. Checkpoint policy, calibración y run I/O; commits separados.
9. El finalizador cambia la versión a candidate/resolved, vincula artifact/hash y marca el artifact available; commit.
10. Recién entonces TRAIN cambia a completed; commit separado.
Por tanto, una model version puede quedar candidate antes de que el TRAIN sea completed.
EVALUATE:
1. Resolver previamente model version y TRAIN.
2. INSERT EVALUATE con status='started'; commit.
3. INSERT de run_lineage y metadata del EVALUATE; commit.
4. Ejecutar evaluación y escribir archivos.
5. Métricas, predicciones, artefactos, dataset images y run I/O; múltiples commits.
6. EVALUATE cambia a completed; último commit.
EVALUATE no crea model version. El linaje se confirma antes de calcular métricas y antes de saber si la evaluación finalizará correctamente.
5. Punto seguro para actualizar elegibilidad
El lugar lógico es el cierre de EVALUATE en evaluation/evaluator.py:402-414, pero no debe agregarse simplemente una escritura después de finish_tracking_run().
La transición segura debe reemplazar ese cierre por una primitiva transaccional específica:
1. Bloquear el EVALUATE y el TRAIN padre.
2. Verificar el run_lineage gobernado evaluates_checkpoint_from.
3. Verificar tipos de run y que el TRAIN esté completed.
4. Cambiar EVALUATE a completed.
5. Actualizar el estado de liberación separado del TRAIN a available mediante un UPDATE condicional que vuelva a comprobar el EXISTS.
6. Confirmar una única transacción.
Esto es necesario porque:
- finish_tracking_run() utiliza safe_track();
- safe_track() absorbe excepciones;
- finish_tracking_run() no devuelve una confirmación fiable;
- encadenar otra transacción dejaría una ventana de fallo.
También debe recalcularse elegibilidad cuando:
- se inserta linaje por backfill para un EVALUATE ya completado;
- un TRAIN se completa después de su EVALUATE;
- se corrige o elimina linaje;
- cambia posteriormente el estado de alguno de los runs.
runs.status debe seguir representando ejecución y permanecer completed. available/productive necesita una columna o entidad separada de liberación.
Estado actual del esquema
runs tiene 51 columnas de identidad, ejecución, timestamps, configuración, entrenamiento y metadata. Posee PK, FKs y un CHECK JSON, pero:
- no tiene columna persistida de liberación;
- no restringe el vocabulario de run_type o status;
- no valida transiciones;
- tiene índices separados para run_type y status, pero ninguno compuesto para elegibilidad.
run_lineage posee PK, UNIQUE(parent_run_id, child_run_id, relationship_type), checks de relación/confidence, FKs y ownership compuesto de model version/artifact. Su trigger valida training → evaluation, pero no exige estados completed. Tampoco impide que un mismo EVALUATE se vincule a varios TRAIN.
stage2_model_publications tiene checks estructurales y FKs, pero no exige en base de datos:
- TRAIN de tipo training y completed;
- EVALUATE de tipo evaluation y completed;
- linaje directo entre los IDs guardados;
- model version perteneciente al TRAIN;
- un único activo por datasource/scope.
El índice activo único actual es por (model_version_id, scope), no por slot de publicación.
6. SQL read-only utilizado
Las consultas se ejecutaron mediante la conexión operativa del backend dentro de una transacción READ ONLY, finalizada con rollback.
Conteos principales:
WITH completed_evaluations AS (
    SELECT
        rl.parent_run_id,
        COUNT(DISTINCT child.id)::integer AS completed_evaluation_count
    FROM run_lineage rl
    JOIN runs child ON child.id = rl.child_run_id
    WHERE rl.relationship_type = :relationship
      AND child.run_type = :evaluation
      AND child.status = :completed
    GROUP BY rl.parent_run_id
),
eligible_training AS (
    SELECT training.id
    FROM runs training
    JOIN completed_evaluations ce ON ce.parent_run_id = training.id
    WHERE training.run_type = :training
      AND training.status = :completed
),
active_publications AS (
    SELECT publication.*
    FROM stage2_model_publications publication
    WHERE publication.scope = :scope
      AND publication.status = :active
      AND publication.is_active
),
violating_publications AS (
    SELECT publication.id
    FROM active_publications publication
    LEFT JOIN runs training ON training.id = publication.training_run_id
    WHERE training.id IS NULL
       OR training.run_type <> :training
       OR training.status <> :completed
       OR NOT EXISTS (
            SELECT 1
            FROM run_lineage rl
            JOIN runs evaluation ON evaluation.id = rl.child_run_id
            WHERE rl.parent_run_id = publication.training_run_id
              AND rl.relationship_type = :relationship
              AND evaluation.run_type = :evaluation
              AND evaluation.status = :completed
       )
)
SELECT
    (SELECT COUNT(*) FROM runs WHERE run_type = :training) AS train_total,
    (SELECT COUNT(*) FROM runs
      WHERE run_type = :training AND status = :completed) AS train_completed,
    (SELECT COUNT(*) FROM eligible_training) AS train_completed_with_evaluate,
    (SELECT COUNT(*) FROM active_publications) AS active_publications,
    (SELECT COUNT(*) FROM violating_publications) AS violations,
    (SELECT COUNT(*) FROM completed_evaluations
      WHERE completed_evaluation_count > 1) AS trains_with_multiple_evaluates;
Model versions por TRAIN:
WITH project_training AS (
    SELECT training.id
    FROM runs training
    JOIN experiments experiment ON experiment.id = training.experiment_id
    WHERE experiment.project_name = :project
      AND training.run_type = :training
),
version_counts AS (
    SELECT
        training.id,
        COUNT(version.id)::integer AS versions_per_train
    FROM project_training training
    LEFT JOIN model_versions version
      ON version.training_run_id = training.id
    GROUP BY training.id
)
SELECT versions_per_train, COUNT(*)::integer AS train_count
FROM version_counts
GROUP BY versions_per_train
ORDER BY versions_per_train;
Integridad estricta de publicaciones activas:
SELECT
    COUNT(*) AS active_publications,
    COUNT(*) FILTER (
        WHERE training.run_type <> :training
           OR training.status <> :completed
    ) AS invalid_training_state,
    COUNT(*) FILTER (
        WHERE evaluation.run_type <> :evaluation
           OR evaluation.status <> :completed
    ) AS invalid_evaluation_state,
    COUNT(*) FILTER (WHERE lineage.id IS NULL) AS missing_direct_lineage,
    COUNT(*) FILTER (
        WHERE version.training_run_id IS DISTINCT FROM publication.training_run_id
    ) AS model_version_training_mismatch
FROM stage2_model_publications publication
JOIN runs training ON training.id = publication.training_run_id
JOIN runs evaluation ON evaluation.id = publication.evaluation_run_id
JOIN model_versions version ON version.id = publication.model_version_id
LEFT JOIN run_lineage lineage
  ON lineage.parent_run_id = publication.training_run_id
 AND lineage.child_run_id = publication.evaluation_run_id
 AND lineage.relationship_type = :relationship
WHERE publication.datasource = :datasource
  AND publication.scope = :scope
  AND publication.status = :active
  AND publication.is_active;
Para esquema se consultaron information_schema.columns, pg_constraint, pg_indexes, pg_trigger, alembic_version y schema_migrations; no se consultaron filas clínicas ni identificadores de runs.
7. Conteos obtenidos
Los conteos globales y los restringidos a malaria_dl_local_project coinciden para TRAIN.
Métrica	Conteo
TRAIN totales	24
TRAIN completed	24
TRAIN completed con EVALUATE completed vía linaje	24
Publicaciones Stage 2 totales	4
Publicaciones Stage 2 activas	1
Activas que incumplen la regla	0
TRAIN con más de un EVALUATE completed	12
TRAIN con 1 EVALUATE completed	12
TRAIN con 2 EVALUATE completed	12
Model versions totales asociadas a TRAIN	36
TRAIN con 0 model versions	0
TRAIN con 1 model version	12
TRAIN con 2 model versions	12


Cobertura adicional:
- 12 model versions no tienen EVALUATE completed específico.
- 12 tienen uno.
- 12 tienen dos.
- Los 36 linajes de evaluaciones completadas conservan model version y artifact.
- La publicación activa pasa también la validación estricta de sus IDs guardados.
8. Contradicciones encontradas
1. La elegibilidad ya se calcula dinámicamente en dos servicios, pero no se persiste en TRAIN.
2. runs.status es estado de ejecución; cambiarlo a available/productive rompería la regla que exige TRAIN.status='completed'.
3. Stage2PublicationService devuelve available antes de publicar, pero una publicación activa pasa directamente a production.
4. El endpoint de publicación crea la publicación y luego habilita automáticamente el deployment. Esto contradice la futura promoción manual a productive.
5. Publicación y deployment usan transacciones distintas: puede quedar una publicación activa si el enablement posterior falla.
6. La integridad semántica de publicaciones depende del servicio, no de constraints PostgreSQL.
7. La selección de EVALUATE en Stage2PublicationService._context() no exige que su model_version_id coincida con la versión consultada.
8. La regla literal es por TRAIN, pero 12 TRAIN tienen dos versiones y 12 versiones concretas carecen de evaluación. Persistir elegibilidad del TRAIN no significa automáticamente que todas sus versiones estén evaluadas.
9. La model version se vuelve candidate antes de que el TRAIN quede completed.
10. El cierre de tracking absorbe errores y no demuestra que la escritura terminal haya ocurrido.
11. Coexisten Alembic y el ledger SQL legacy.
12. La configuración actual del rol del servicio db no coincide con el cluster persistido.
9. Archivos que deberían cambiar después
En fases posteriores:
- docker-compose.override.yml: mounts RO mínimos para Alembic.
- Nueva migración bajo alembic/versions/: estado de liberación, checks, índices, backfill y mecanismo de invariantes.
- persistence/run_repository.py: cierre atómico específico de EVALUATE.
- persistence/tracking.py: propagar éxito/fallo real del cierre.
- evaluation/evaluator.py: utilizar el cierre transaccional.
- persistence/lineage.py y scripts/backfill_run_lineage.py: refresco idempotente para linajes agregados posteriormente.
- stage2_publication_service.py y stage2_availability_service.py: semántica única de available y productive.
- backend_api/app/routes/governance.py: separar disponibilización de promoción productiva.
- Schemas/tipos frontend y Runs.tsx/Stage2ReleaseDetail.tsx.
- Pruebas PostgreSQL de migración, concurrencia, múltiples EVALUATE, múltiples padres, backfill y rollback.
10. Riesgos de migración
- El baseline 20260726_00 es stamp-only: una base fresca no puede reconstruirse sólo con Alembic.
- Las últimas migraciones prohíben downgrade.
- El backfill inicial marcaría los 24 TRAIN como available.
- Debe definirse si la publicación activa actual implica productive; la regla futura dice que esa promoción es manual.
- Un CHECK no puede imponer por sí solo un EXISTS entre tablas. Se necesita transacción gobernada, trigger o reconciliación.
- Cambios posteriores de status o eliminación de linaje pueden volver obsoleto un estado persistido.
- Debe definirse la precedencia entre múltiples EVALUATE y múltiples model versions.
- El índice de singleton productivo/publicado debe diseñarse explícitamente por datasource/scope.
- La doble autoridad de migraciones debe resolverse antes de introducir el nuevo objeto.
- El rol/configuración del volumen debe verificarse antes de backup o migración.
- Sin restauración ensayada, la ausencia de downgrade vuelve insuficiente un simple backup nominal.
11. Comandos Docker posteriores
Validación read-only, después de corregir los mounts:
docker compose config --quiet
docker compose ps
docker compose exec backend python -m alembic current
docker compose exec backend python -m alembic heads
docker compose exec backend python -m alembic history
docker compose exec backend python -m alembic upgrade head --sql
docker compose config completo también es seguro, pero su salida debe sanitizarse antes de compartirla.
Tras aprobar la migración:
docker compose up -d --force-recreate backend
make db-backup
docker compose exec backend python -m alembic current
docker compose exec backend python -m alembic heads
docker compose exec backend python -m alembic upgrade head
docker compose exec backend python -m alembic current
docker compose exec backend python -m alembic heads
No debe ejecutarse upgrade head mientras Alembic siga oculto, el backup no haya sido validado o persista la discrepancia del rol PostgreSQL.