---
name: testing-audit-guardian
description: Exigir pruebas y evidencia verificable sin imponer prerrequisitos científicos obsoletos.
---

# testing-audit-guardian

## Reglas
- Diferenciar decisiones acordadas, comportamiento observado y evidencia de pruebas.
- Pruebas de persistencia deben comprobar transacciones, aislamiento, fallos SQL y trazabilidad sin destruir datos científicos.
- Ejecutar pruebas mediante mecanismo apropiado al componente y entorno; no imponer Docker/Makefile universalmente.
- No imponer `TRAIN + EVALUATE` como condición universal de Stage 2 ni como requisito de TEST.
- Documentar qué se verificó, con comando, resultado y fecha; sin declarar aprobado lo no ejecutado.
- Consultar estado documental y contratos actuales antes de usar banners como criterio de vigencia.

## Referencias
- `references/verification-matrix.md`
- `references/legacy-original.md` (histórica).
