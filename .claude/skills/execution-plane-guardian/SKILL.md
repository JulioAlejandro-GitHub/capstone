---
name: execution-plane-guardian
description: Activa este skill cuando se discuta la arquitectura de ejecución, el despliegue de campañas de ML, agentes locales (Mac), Docker Executor, o el diagrama de control/execution plane.
---

# Execution Plane & Architecture Guardian

## Summary
Este skill define la arquitectura bimodal (Docker/Linux y Local/Mac) para la ejecución de campañas de Machine Learning, asegurando que ambos entornos se reporten centralizadamente a PostgreSQL como fuente de verdad[cite: 4].

## When to Use
* Al diseñar o depurar la ejecución de campañas de ML (CampaignService, ExecutionScheduler o scripts como run_train_all_models.py).[cite: 4].
* Al configurar entornos de ejecución (Docker vs. Local Mac Agent)[cite: 4].
* Al tratar con el reporte de resultados y almacenamiento de artefactos (métricas, checkpoints, imágenes)[cite: 4].

## Core Architecture Principles
1. **Control Plane Centralizado:** El `Backend FastAPI / Campaign Core` (con servicios como `CampaignService`, `ModelRegistry`, `ExecutionScheduler`) orquesta todo el sistema[cite: 4].
2. **PostgreSQL como Fuente de Verdad Absoluta:** Toda la orquestación (`Campaign / Run / Result / Audit`) y los resultados de estado/métricas deben persistirse obligatoriamente en la base de datos PostgreSQL[cite: 4].
3. **Execution Plane Bimodal:**
   * Las ejecuciones pueden ocurrir en dos entornos distintos, y el sistema debe soportar ambos[cite: 4]:
     * **Docker Executor:** Entorno aislado sobre `Python / Linux`[cite: 4].
     * **Local Mac Agent:** Ejecución nativa para aprovechar hardware local sobre `Python / Darwin`[cite: 4].
4. **Reporte Unificado:** Sin importar si la ejecución es Docker o Local, ambas deben utilizar un `RunReporter` que se comunique con el `ResultService` del backend[cite: 4].
5. **Separación de Almacenamiento Post-Ejecución:**
   * **Métricas/Evidencias/Estado:** Se guardan en `PostgreSQL`[cite: 4].
   * **Archivos Pesados (checkpoints, imágenes):** Se dirigen al `Artifact Storage`[cite: 4].


# Política: Principio Arquitectónico Obligatorio: Verdad Única de Estructura PostgreSQL

## 1. Declaración del Principio
**La estructura vigente de PostgreSQL es la única estructura válida del sistema.** El software debe operar bajo una confianza absoluta en el esquema actual, delegando la validación estructural por completo al motor de base de datos en tiempo de ejecución.

## 2. Restricciones y Prohibiciones Explícitas (Anti-Patterns)
El software tiene estrictamente prohibido realizar validaciones de compatibilidad previas o en paralelo. Específicamente, el componente:
* **No verifica** versiones de la base de datos de manera explícita.
* **No verifica** revisiones ni estados de herramientas de migración como **Alembic**.
* **No compara** contratos de esquema o metadatos antes de ejecutar queries.
* **No realiza** preflights ni chequeos previos de compatibilidad estructural.
* **No consulta** tablas de migraciones (`alembic_version`, etc.) para decidir si puede o no funcionar.
* **No mantiene** ni ejecuta caminos de código alternativos para soportar esquemas históricos o versiones antiguas.

## 3. Modo de Ejecución
* El software **ejecuta directamente su SQL** contra PostgreSQL.
* **Manejo de Errores:** Si una operación falla debido a que el SQL enviado no coincide con la estructura vigente de la base de datos, la acción correctiva obligatoria es **corregir el código SQL**, no adaptar el entorno ni añadir capas de compatibilidad hacia atrás.

## 4. Gestión de Integridad de Datos
La integridad de los datos sigue siendo responsabilidad exclusiva de PostgreSQL. Se confía plenamente en sus restricciones nativas:
* `PRIMARY KEY`
* `FOREIGN KEY`
* `UNIQUE`
* `CHECK`
* `NOT NULL`
* Triggers y funciones que implementen reglas legítimas de integridad en la base de datos.

*Nota de Cumplimiento:* **No confundir** una restricción legítima de integridad (excepciones lanzadas por el motor ante inserts/updates inválidos) con una comprobación artificial de versión o compatibilidad estructural en la capa de aplicación.


## Gotchas
* No asumas que todo se ejecuta en Docker; el `Local Mac Agent` es un entorno válido y soportado por diseño para el plano de ejecución[cite: 4].
* Asegúrate de que cualquier nuevo script de ejecución o agente implemente el contrato del `RunReporter` para no romper el ciclo de feedback hacia el backend[cite: 4].