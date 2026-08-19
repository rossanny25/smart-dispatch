# Backlog De Tareas Y Estado Del Proyecto

Este documento detalla el estado actual del proyecto Smart Dispatch IA. Fue
actualizado para reflejar la implementacion real: FastAPI, frontend vanilla,
Docker, Render y documentacion tecnica de producto.

---

## Fase 1: Diseno Conceptual E Inicializacion (Completado)

- [x] Crear e inicializar la estructura básica del repositorio de especificaciones.
- [x] Redactar los 14 archivos de especificaciones funcionales en `spec/`.
- [x] Desarrollar y validar los prompts para los 5 agentes en `prompts/`.
- [x] Crear el archivo de contexto general `docs/CONTEXT.md`.

## Fase 2: Aplicacion Real Y Demo Ejecutable (Completado)

- [x] Implementar backend Python/FastAPI.
- [x] Mantener frontend estatico con HTML, CSS y JavaScript vanilla.
- [x] Implementar rutas legacy `/api/*` para la demo visible.
- [x] Implementar rutas canonicas `/api/v1/*` para contratos y persistencia.
- [x] Crear orquestacion deterministica con `DispatchOrchestrator`.
- [x] Aplicar reglas duras antes del scoring.
- [x] Separar score objetivo y confianza de recomendacion.
- [x] Configurar persistencia SQLite con migraciones Alembic.
- [x] Mover datos demo a seeds JSON versionados.
- [x] Agregar reset de demo desde seeds.
- [x] Dockerizar la aplicacion en puerto `8050`.
- [x] Publicar aplicacion en Render Free.
- [x] Subir repositorio a GitHub.

## Fase 3: Entrega Final Academica (Completado)

- [x] Agregar README de ejecucion y configuracion.
- [x] Agregar runbook con acciones tecnicas.
- [x] Capturar screenshots reales del frontend.
- [x] Exportar evidencia API y logs Docker.
- [x] Documentar arquitectura y UML.
- [x] Documentar tabla de tecnologias con justificacion.
- [x] Documentar sesion real de uso.
- [x] Crear autoevaluacion UX/UI con heuristicas de Nielsen.
- [x] Crear log de ciberseguridad con riesgos y mitigaciones.
- [x] Documentar uso de IA en co-work.
- [x] Incluir reflexion sobre LLM/SLM local.
- [x] Generar informe Markdown final.
- [x] Generar PDF final con capturas embebidas.

## Fase 4: Handoff Para Agentes IA (Completado)

- [x] Mantener `_bmad-output/project-context.md` como reglas tecnicas profundas.
- [x] Agregar `AGENTS.md` en la raiz del repositorio.
- [x] Agregar `docs/ai-project-status.md` como estado vivo del proyecto.
- [x] Enlazar archivos de contexto desde README e indice de docs.

## Fase 5: Mejoras Futuras Opcionales

- [x] Agregar demo guiada dentro de la interfaz.
- [x] Mostrar reglas duras por tecnico antes del score.
- [x] Separar visualmente score objetivo y confianza de recomendacion.
- [x] Agregar login single-user para proteger UI y API.

## Fase 6: Administracion Operativa (En progreso)

- [x] Crear usuarios persistidos en SQLite.
- [x] Crear usuario inicial `admin` con clave `smart2026AI`.
- [x] Validar login contra la base de datos.
- [x] Agregar roles basicos `admin`, `tecnico` y `dispatcher`.
- [x] Agregar panel admin para listar, crear y editar usuarios.
- [x] Proteger rutas de administracion para rol `admin`.
- [x] Agregar accion visible de olvido de contraseña con recuperacion manual.
- [x] Revalidar sesiones contra SQLite en cada request protegido.
- [x] Agregar idempotencia basica en creacion/edicion de usuarios.
- [x] Configurar secreto de sesion generado y cookie segura para Render.
- [x] Limitar payload de login para reducir abuso.
- [x] Persistir tecnicos operativos en SQLite.
- [x] Crear panel admin para crear y editar tecnicos.
- [x] Agregar horarios y disponibilidad editable por tecnico.
- [x] Mostrar criterios de seleccion, reglas duras y efecto de memoria en UI.
- [x] Rechazar solicitudes de servicio con texto no entendible.
- [ ] Crear fichas completas de tecnicos con contacto/documentos/auditoria.
- [ ] Agregar calendario de visitas por tecnico.
- [ ] Agregar vista de mapa sin dependencia paga.
- [ ] Migrar ordenes demo desde JSON bootstrap a datos operativos SQLite.
- [ ] Mostrar `DispatchRun` canonico de `/api/v1` en el frontend.
- [ ] Implementar decision humana y outcome completo sobre API canonica.
- [ ] Mover endpoints admin al sobre canonico completo de `/api/v1`.
- [ ] Integrar escrituras admin al Unit of Work principal.
- [ ] Agregar escenario explicito de `NO_FEASIBLE_CANDIDATES`.
- [ ] Mostrar estados canonicos `CAPTURE`, `ANALYZE`, `PLAN`, `EVALUATE` y `WAIT_FOR_DECISION`.
- [ ] Evaluar Ollama como adaptador local opcional de `ANALYZE`.
- [ ] Expandir autenticacion solo si el proyecto deja de ser single-user.
