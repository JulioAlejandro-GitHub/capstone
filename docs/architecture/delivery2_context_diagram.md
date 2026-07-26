# Diagrama de contexto — Entrega 2

Estado: objetivo aprobado para Architecture Baseline v1.1. La plataforma es una **plataforma científica experimental de apoyo al análisis de imágenes microscópicas de frotis sanguíneo**.

```mermaid
flowchart LR
  OP[Operator] -->|registra muestra, carga imagen, inicia análisis| SYS[Capstone Etapa 2]
  RS[Researcher] -->|selecciona modelos, consulta resultados| SYS
  RV[Reviewer] -->|confirma, corrige y anota| SYS
  RO[Read only] -->|consulta resultados experimentales| SYS
  AD[Administrator] -->|usuarios, políticas, publicaciones y default| SYS
  SYS -->|metadatos, cola, auditoría| PG[(PostgreSQL)]
  SYS -->|originales y artefactos inmutables/versionados| FS[(Filesystem administrado)]
  SYS -->|clasificación celular| PUB[Modelos publicados Etapa 2]
  SYS -->|polling, boxes, crops, resultados y avisos| WEB[React Workbench]
```

Límites:

- No diagnostica, no reemplaza al microscopista y no integra LIS/HIS.
- PostgreSQL no almacena imágenes como `BYTEA`.
- La calidad rechazada termina antes de crear un `analysis_job`.
- Cada corrección humana se conserva aparte del resultado automático.

