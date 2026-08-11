# Smart Dispatch IA - Informe Final

## Primera Pagina: Links Del Proyecto

> Completar estos links antes de exportar a PDF. El docente evalua primero el proyecto publicado.

| Recurso | Link |
| --- | --- |
| Aplicacion en vivo | Pendiente de publicar |
| Repositorio GitHub | `git@github.com:rossanny25/smart-dispatch.git` |
| Demo Docker local | `http://127.0.0.1:8050` |
| Guia de ejecucion | `docs/runbook.md` |

## 1. Resumen Ejecutivo

Smart Dispatch IA es un prototipo educativo para asistir decisiones de despacho tecnico en servicios de campo. La evolucion realizada convierte la idea conceptual de medio ciclo en una aplicacion ejecutable: una interfaz web, una API local, persistencia SQLite, contratos de datos, reglas duras de elegibilidad, scoring explicable, confianza independiente y orquestacion deterministica auditable.

El foco del proyecto no es reemplazar al despachador, sino ayudarlo a tomar una decision mejor documentada. El sistema recomienda tecnicos solo despues de aplicar restricciones operativas no negociables, calcula un puntaje objetivo para candidatos elegibles y muestra evidencia estructurada para explicar la recomendacion.

## 2. Objetivo Del Proyecto

El objetivo es demostrar una arquitectura de orquestacion agentica ciclica con memoria persistente para asignacion de tecnicos. El sistema modela el ciclo:

```text
CAPTURE -> ANALYZE -> PLAN -> EVALUATE -> WAIT_FOR_DECISION
```

Las etapas actuan como agentes especializados, pero no controlan el flujo. El `DispatchOrchestrator` es la unica pieza autorizada para avanzar estados y registrar evidencia. Esta decision responde directamente al feedback docente: pasar de una descripcion conceptual a un mecanismo tecnico verificable.

## 3. Arquitectura

Ver diagramas detallados en `docs/final-architecture-diagrams.md`.

La arquitectura actual es un monolito modular hexagonal:

- Frontend vanilla HTML/CSS/JavaScript.
- API FastAPI bajo `/api/v1` y adaptadores legacy `/api/*`.
- Capa de aplicacion con comandos.
- Dominio con politicas puras de analisis, elegibilidad, scoring, confianza y despacho.
- Persistencia SQLite con SQLAlchemy Core y migraciones Alembic.
- Docker para ejecucion reproducible en puerto `8050`.

## 4. UML Y Modelo De Datos

El modelo central gira alrededor de:

- `WorkOrder`: incidente recibido.
- `DispatchRun`: ejecucion auditable para una orden.
- `RunSnapshot`: copia inmutable de entradas y configuracion.
- `StageExecution`: evidencia de cada etapa.
- `StateTransition`: historial de estados.
- `Technician`: candidato evaluado.
- `EligibilityCandidate`: resultado de reglas duras.
- `ScoredTechnician`: puntaje objetivo para candidatos elegibles.
- `ConfidenceOutput`: confianza, advertencias y explicacion.

Ver UML en `docs/final-architecture-diagrams.md`.

## 5. Tecnologias Usadas

| Tecnologia | Uso | Justificacion |
| --- | --- | --- |
| Python 3.12 | Backend principal | Lenguaje simple para prototipo academico, con buen soporte web y testing. |
| FastAPI | API HTTP | Contratos claros, OpenAPI automatico y ejecucion ASGI. |
| Pydantic v2 | Validacion | Modelos estrictos con campos desconocidos prohibidos. |
| SQLAlchemy Core | Persistencia | Acceso SQL explicito sin esconder las invariantes del dominio. |
| Alembic | Migraciones | Evolucion controlada del esquema SQLite. |
| SQLite | Base local | Persistencia liviana, reproducible y suficiente para demo academica. |
| Vanilla HTML/CSS/JS | Frontend | Mantiene el alcance simple y auditable sin framework extra. |
| Docker / Compose | Ejecucion | Permite levantar la app en `8050` sin depender del entorno Python local. |
| pytest | Verificacion | Pruebas unitarias, integracion y contrato. |

## 6. Funcionamiento De La Aplicacion

La aplicacion permite:

1. Visualizar ordenes y tecnicos.
2. Simular una recomendacion de despacho.
3. Revisar candidatos, descartes y recomendacion.
4. Consultar memoria de aprendizaje legacy.
5. Ejecutar endpoints canonicos `/api/v1` para Work Orders y Dispatch Runs.

La demo recomendada se levanta con:

```bash
docker compose up --build
```

URL:

```text
http://127.0.0.1:8050
```

## 7. Registro De Sesion Real

Ver `docs/usage-session-log.md`.

Capturas ya generadas para el PDF:

- `docs/evidence/01-dashboard-full.png`: inicio de la aplicacion, ordenes, tecnicos y memoria.
- `docs/evidence/02-dispatch-result.png`: simulacion completada y recomendacion.
- `docs/evidence/03-recommendation-approved.png`: aprobacion de recomendacion y modal de cierre.
- `docs/evidence/04-learning-completed.png`: orden completada despues del cierre.
- `docs/evidence/api-technicians.json`: evidencia API de tecnicos.
- `docs/evidence/api-orders-after-session.json`: evidencia API de orden completada.
- `docs/evidence/docker-session.log`: log real de Docker/Uvicorn y requests.

## 8. Autoevaluacion UX/UI

Ver `docs/nielsen-ux-review.md`.

Resultado general: la interfaz es adecuada para una demo academica porque muestra ordenes, tecnicos y simulacion en una consola clara. Las mejoras pendientes estan en accesibilidad completa, reduccion de dependencia visual, mensajes de error mas guiados y una vista mas explicita del estado canonico `/api/v1`.

## 9. Log De Ciberseguridad

Ver `docs/cybersecurity-log.md`.

Riesgos principales documentados:

- Exposicion accidental fuera de local.
- Falta de autenticacion para uso productivo.
- Datos sensibles de ubicacion/direccion.
- Dependencias externas/CDN en frontend.
- Limites de payload y errores seguros.
- Persistencia local y backups.

## 10. Uso De IA En Co-Work

Ver `docs/ai-cowork-log.md`.

La IA se uso como colaborador tecnico para:

- Reconciliar feedback docente.
- Formalizar PRD/arquitectura/historias.
- Implementar orquestacion deterministica.
- Crear pruebas.
- Dockerizar el proyecto.
- Preparar documentacion de entrega.

Tambien requirio correccion humana en decisiones de alcance, rutas de publicacion y validacion real del entorno.

## 11. Reflexion Sobre LLM/SLM Local

Un LLM o SLM local podria integrarse como adaptador opcional de ANALYZE. Su rol seria convertir texto libre del incidente en campos estructurados, pero sin controlar estados ni saltear reglas duras. La salida del modelo deberia pasar por los mismos contratos Pydantic y registrar metadata de modelo/proveedor.

Ventajas:

- Mejor comprension de lenguaje natural.
- Mayor privacidad si corre localmente.
- Demo academica offline con Ollama.

Limitaciones:

- Menor precision frente a modelos cloud grandes.
- Requiere hardware local.
- Puede tener mas latencia.
- Necesita validacion estricta para no inventar datos.

La decision arquitectonica recomendada es mantener deterministica la elegibilidad, scoring, confianza y transiciones, usando LLM solo como ayuda en interpretacion textual.

## 12. Estado Actual Y Proximos Pasos

Estado actual:

- Aplicacion ejecutable local y por Docker.
- Puerto Docker: `8050`.
- API y frontend funcionales.
- Persistencia SQLite y migraciones.
- Datos demo cargados desde semillas reproducibles en `data/seeds/`.
- Documentacion base de entrega.
- Tests relevantes verificados.

Pendiente antes de entregar:

- Publicar repositorio en GitHub.
- Mantener backend, frontend, Docker, docs, spec y evidencia en un unico monorepo para facilitar la evaluacion.
- Definir si habra deploy web publico o si GitHub + Docker sera el artefacto publicado.
- Agregar links reales en la primera pagina.
- Tomar capturas de pantalla.
- Exportar este informe a PDF de 10 a 20 paginas.
- Opcional: incluir captura de Ollama respondiendo una pregunta del proyecto.
