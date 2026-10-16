---
name: hybrid-architecture-runtime
description: Activa este skill al discutir cómo levantar servicios, ejecutar campañas de ML, testing, infraestructura o el diagrama de control/execution plane.
---

# Hybrid Architecture & Runtime Guardian

## Summary
El sistema opera bajo una arquitectura híbrida dividida en dos planos: un Control Plane centralizado (estrictamente en Docker) y un Execution Plane bimodal (Docker o Mac Local)[cite: 4]. 

## When to Use
* Al levantar, detener o configurar la API, Frontend o Base de Datos.
* Al orquestar campañas de ML (`CampaignService`, `ExecutionScheduler`)[cite: 4].
* Al ejecutar scripts de inferencia, entrenamiento o testing.

## Core Rules & Topology
1. **Control Plane (Estricto en Docker):**
   * El `Backend FastAPI / Campaign Core`, el Frontend en React y `PostgreSQL` (la fuente de verdad absoluta) DEBEN ejecutarse exclusivamente mediante `docker-compose.yml` y el `Makefile`[cite: 4].
   * Bloquea la ejecución manual (ej. `uvicorn` o `npm run`) en el host para estos componentes.
2. **Execution Plane (Bimodal):**
   * La carga computacional de ML se ejecuta en agentes separados que reportan al Control Plane[cite: 4]. Soporta dos vías legales:
     * **Docker Executor:** Entorno aislado sobre `Python / Linux`[cite: 4].
     * **Local Mac Agent:** Ejecución nativa (`Python / Darwin`) invocada mediante scripts manuales (ej. `python run_train_all_models.py`)[cite: 4].
3. **El Contrato del RunReporter:**
   * Sin importar dónde se ejecute el modelo (Linux o Mac), el agente DEBE usar el `RunReporter` para enviar telemetría al `ResultService` del backend[cite: 4].
4. **Almacenamiento Separado:**
   * Las métricas, auditorías y estados se envían a PostgreSQL (vía backend)[cite: 4].
   * Los archivos pesados (checkpoints, imágenes) se envían directamente al `Artifact Storage`[cite: 4].

## Gotchas
* Nunca intentes dockerizar un script de ML si el usuario especifica que quiere usar el hardware local de su Mac (Darwin)[cite: 4].
* No permitas que el backend FastAPI se ejecute fuera de Docker; su lugar está en el Control Plane[cite: 4].