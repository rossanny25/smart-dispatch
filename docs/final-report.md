# Smart Dispatch IA - Informe Final

## Primera Pagina: Links Del Proyecto

| Recurso | Link |
| --- | --- |
| Aplicacion en vivo | https://smart-dispatch-q4xk.onrender.com |
| Repositorio GitHub | https://github.com/rossanny25/smart-dispatch |
| Demo Docker local | http://127.0.0.1:8050 |
| Guia de ejecucion | docs/runbook.md |
| Evidencia de sesion | docs/usage-session-log.md |

Nota de hosting: la aplicacion publicada usa Render Free. Si la instancia estuvo inactiva, la primera carga puede demorar aproximadamente 50 segundos o mas mientras el servicio despierta.

## 1. Resumen Ejecutivo

Smart Dispatch IA es un prototipo funcional de asistencia al despacho tecnico en servicios de campo. El proyecto convierte un modelo conceptual de orquestacion agentica y memoria persistente en una aplicacion web publicada, ejecutable con Docker y documentada con evidencia tecnica reproducible.

El sistema ayuda a decidir que tecnico conviene asignar a una orden de trabajo. Para hacerlo, separa el problema en etapas: captura de informacion, analisis de requerimientos, planificacion, evaluacion de restricciones, scoring, confianza y aprendizaje. La aplicacion no reemplaza al despachador: funciona como soporte a la decision y conserva evidencia de por que se recomienda un tecnico.

La evolucion principal frente al trabajo teorico inicial es que la orquestacion deja de ser una descripcion general y pasa a estar formalizada como una maquina de estados deterministica. Las reglas duras se aplican antes del ranking, la funcion objetivo esta versionada, la confianza se calcula separada del puntaje y la memoria persistente queda tratada como evidencia controlada, no como una excusa para saltear restricciones.

## 2. Contexto Y Problema

En operaciones de campo, un despachador suele asignar tecnicos con informacion incompleta: tipo de incidente, zona, urgencia, habilidades requeridas, disponibilidad, carga de trabajo, distancia, clima, trafico y experiencia historica. Una mala asignacion puede causar demoras, incumplimiento de SLA, sobrecarga de tecnicos o decisiones poco explicables.

El problema no es solo seleccionar "el tecnico mas cercano". Tambien hay restricciones que no deberian negociarse: disponibilidad, certificaciones, turno, carga maxima de jornada, limite de conduccion y elementos de seguridad. Ademas, existen objetivos que compiten entre si: llegar rapido, balancear carga, respetar SLA y aprender de casos anteriores.

Por eso el sistema se plantea como una ayuda inteligente pero controlada: primero determina factibilidad, luego rankea candidatos y finalmente expone evidencia para que el humano decida.

## 3. Objetivo Del Proyecto

El objetivo final es demostrar una arquitectura de orquestacion agentica ciclica con memoria persistente aplicada a despacho tecnico. El prototipo debe existir, funcionar y estar publicado, no solo estar explicado en un documento.

Objetivos concretos:

- Publicar una aplicacion web funcional.
- Mostrar un ciclo agentico visible y reproducible.
- Implementar una API backend con persistencia local.
- Registrar evidencia tecnica de una sesion real.
- Documentar arquitectura, UML, tecnologias y decisiones.
- Evaluar UX/UI con heuristicas de Nielsen.
- Identificar riesgos de ciberseguridad y mitigaciones.
- Reflexionar sobre como integrar un LLM o SLM local.

## 4. Evolucion Desde El Trabajo De Medio Ciclo

La version conceptual inicial presentaba una propuesta con cinco agentes: Captura, Analizador, Planificador, Evaluador y Aprendizaje. La revision tecnica posterior senalo que la idea era coherente, pero que faltaba formalizar los mecanismos internos clave.

Principales mejoras realizadas:

| Observacion del feedback | Evolucion implementada |
| --- | --- |
| Orquestador ambiguo | Se adopto una maquina de estados deterministica controlada por `DispatchOrchestrator`. |
| Memoria persistente poco formalizada | Se separo evidencia seed, runtime SQLite y memoria de aprendizaje legacy documentada. |
| Funcion objetivo descriptiva | Se definio scoring con componentes, pesos, penalizaciones y version de configuracion. |
| Aprendizaje generico | Se limito a aprendizaje incremental/evidencial, evitando prometer fine-tuning. |
| Falta de metricas concretas | Se documentaron KPIs y evidencia requerida para evaluacion futura. |
| Incertidumbre y explicabilidad incompletas | Se agrego confianza independiente, warnings y explicaciones estructuradas. |
| Falta de evidencia de app real | Se publico en Render, se dockerizo y se capturaron screenshots/logs reales. |

## 5. Arquitectura General

La arquitectura objetivo es un monolito modular hexagonal con pipeline deterministico. Se eligio monorepo porque el frontend es estatico y FastAPI puede servir API y UI desde el mismo proceso. Esto reduce friccion operativa: un repositorio, un README, un comando Docker y una ruta clara de despliegue.

Componentes principales:

- `frontend/`: interfaz HTML, CSS y JavaScript vanilla.
- `app/api/v1`: API canonica versionada.
- `app/application`: comandos y casos de uso.
- `app/domain`: politicas puras de negocio.
- `app/adapters`: persistencia, legacy API y etapas deterministicas.
- `app/migrations`: migraciones Alembic.
- `data/seeds`: datos reproducibles de demo.
- `docs`: informe, diagramas, evidencia y runbook.

El diagrama completo esta en `docs/final-architecture-diagrams.md`.

Resumen del flujo:

```text
Browser UI -> FastAPI -> Application Commands -> DispatchOrchestrator
              -> Domain Policies -> SQLite Repositories
```

## 6. Orquestacion Agentica Ciclica

El sistema modela el ciclo de despacho como una secuencia de estados:

```text
CAPTURE -> ANALYZE -> PLAN -> EVALUATE -> WAIT_FOR_DECISION
```

Cada etapa cumple una responsabilidad:

| Etapa | Responsabilidad |
| --- | --- |
| CAPTURE | Normaliza y valida la informacion de entrada. |
| ANALYZE | Deriva categoria, prioridad, SLA, certificaciones y duracion estimada. |
| PLAN | Aplica reglas duras y calcula ranking solo para candidatos elegibles. |
| EVALUATE | Agrega confianza, advertencias y explicacion sin cambiar el ranking. |
| WAIT_FOR_DECISION | Espera la decision humana del despachador. |

La pieza central es `DispatchOrchestrator`: los agentes no pueden avanzar estados por su cuenta. Esto responde a una debilidad teorica del planteo original, donde se mencionaba un "orquestador inteligente" sin definir si era LLM, pipeline fijo o maquina de estados.

## 7. Reglas Duras Y Funcion Objetivo

El prototipo distingue entre restricciones duras y criterios de optimizacion.

Restricciones duras:

- Tecnico disponible.
- Todas las certificaciones requeridas.
- Turno vigente.
- Jornada maxima.
- Limite de conduccion.
- EPP requerido.

Un tecnico que falla una restriccion dura no puede recibir puntaje objetivo. Esta decision evita un problema comun en sistemas basados en IA: permitir que una puntuacion alta o una preferencia aprendida oculte una violacion operativa.

Funcion objetivo:

```text
score = 0.35 * SLA
      + 0.25 * proximidad
      + 0.20 * balance_carga
      + 0.10 * calidad
      + 0.10 * memoria
      - penalizaciones
```

Cada componente se normaliza entre 0 y 100. Los calculos autoritativos usan `Decimal` para evitar errores de punto flotante, y la presentacion redondeada se deja para la frontera HTTP/UI.

## 8. Memoria Persistente Y Datos

El sistema utiliza datos semilla reproducibles, persistencia SQLite y login
single-user para proteger la UI y las rutas API. No incluye panel de
administracion ni roles; la decision se documenta como limite operativo y no
como omision accidental.

Estrategia de datos:

- Tecnicos demo: `data/seeds/technicians.json`.
- Ordenes demo: `data/seeds/orders.json`.
- Memoria inicial: `data/learning_store.json`.
- Runtime SQLite local: `data/smart_dispatch.db`.
- Runtime Docker: volumen `smart_dispatch_data`.

Para resetear datos demo:

```bash
docker compose down -v
docker compose up --build
```

Tambien existe `/api/reset`, que restaura tecnicos y ordenes desde `data/seeds/`.

Alembic se usa para estructura de base de datos, no para contenido demo. Esto mantiene una separacion clara: migraciones para schema, seeds para escenarios reproducibles.

## 9. Tecnologias Usadas

| Tecnologia | Uso | Justificacion |
| --- | --- | --- |
| Python 3.12 | Backend principal | Lenguaje claro, buen ecosistema web y testing. |
| FastAPI | API HTTP | Contratos claros, OpenAPI automatico y soporte ASGI. |
| Pydantic v2 | Validacion | Modelos estrictos y rechazo de campos desconocidos. |
| SQLAlchemy Core | Persistencia | SQL explicito sin acoplar dominio a ORM. |
| Alembic | Migraciones | Control de evolucion del esquema SQLite. |
| SQLite | Base local | Suficiente para un MVP single-user y despliegues livianos. |
| HTML/CSS/JS vanilla | Frontend | Interfaz simple, auditable y sin build complejo. |
| Docker / Compose | Ejecucion | Reproducibilidad local y deploy con Dockerfile. |
| Render Free | Publicacion | Permite link publico evaluable. |
| pytest | Verificacion | Pruebas unitarias, integracion y contrato. |
| BMad Method | Gestion de especificacion | PRD, arquitectura, epicas, historias y trazabilidad. |

## 10. Funcionamiento De La Aplicacion

La aplicacion publicada permite:

1. Abrir el dashboard de despacho.
2. Visualizar ordenes de trabajo y tecnicos.
3. Ajustar factores de entorno como clima, trafico y GPS.
4. Ejecutar una simulacion de despacho.
5. Ver el ciclo de agentes en pantalla.
6. Revisar la recomendacion generada.
7. Aprobar o cambiar el tecnico recomendado.
8. Registrar cierre de servicio y retroalimentacion.
9. Consultar memoria persistente legacy.

URL publica:

```text
https://smart-dispatch-q4xk.onrender.com
```

URL local por Docker:

```text
http://127.0.0.1:8050
```

Comando local:

```bash
docker compose up --build
```

## 11. Evidencia De Sesion Real

Se ejecuto una sesion real con la aplicacion Dockerizada. La evidencia esta documentada en `docs/usage-session-log.md`.

Evidencias capturadas:

| Evidencia | Archivo |
| --- | --- |
| Dashboard inicial | `docs/evidence/01-dashboard-full.png` |
| Resultado de simulacion | `docs/evidence/02-dispatch-result.png` |
| Aprobacion de recomendacion | `docs/evidence/03-recommendation-approved.png` |
| Orden completada | `docs/evidence/04-learning-completed.png` |
| API tecnicos | `docs/evidence/api-technicians.json` |
| API ordenes despues de sesion | `docs/evidence/api-orders-after-session.json` |
| Logs Docker/Uvicorn | `docs/evidence/docker-session.log` |

Resultado observado:

- Orden: Cafeteria Martinez Belgrano, Belgrano.
- Categoria: Electricidad.
- Prioridad: 4.
- Tecnico recomendado: Juan Perez.
- Score visible: 98.
- Tiempo de viaje visible: 8 minutos.
- Duracion estimada visible: 90 minutos.
- Estado final de la orden: completada.

## 12. UX/UI: Autoevaluacion Nielsen

La evaluacion completa esta en `docs/nielsen-ux-review.md`.

Resumen:

| Heuristica | Evaluacion |
| --- | --- |
| Visibilidad del estado | Buena: se muestran etapas del ciclo y recomendacion. |
| Relacion con el mundo real | Buena: usa conceptos de despachador, tecnico, orden, zona y prioridad. |
| Control del usuario | Media: permite aprobar/cambiar, pero falta flujo canonico completo. |
| Consistencia | Buena: paneles y estados tienen estilo uniforme. |
| Prevencion de errores | Media: backend valida mas que la UI. |
| Reconocimiento antes que memoria | Buena: ordenes y tecnicos estan visibles. |
| Flexibilidad | Media: faltan botones directos para escenarios operativos. |
| Diseno minimalista | Medio: visualmente claro, aunque algunas trazas ocupan mucho espacio. |
| Recuperacion de errores | Media: la API tiene errores tipados, la UI debe mostrarlos mejor. |
| Ayuda/documentacion | Buena: README, runbook y docs de entrega. |

Mejoras futuras:

- Mostrar estado canonico `DispatchRun` en frontend.
- Mostrar reglas duras antes del puntaje.
- Separar visualmente score objetivo y confianza.
- Agregar pantalla explicita de `NO_FEASIBLE_CANDIDATES`.
- Mejorar accesibilidad por teclado y etiquetas semanticas.

## 13. Log De Ciberseguridad

La revision completa esta en `docs/cybersecurity-log.md`.

Riesgos y mitigaciones:

| Riesgo | Mitigacion actual |
| --- | --- |
| Exposicion accidental | Default local `127.0.0.1`; Docker/deploy explicitamente configurados; login single-user. |
| Credenciales compartidas | Cookie firmada y credencial configurable; usuarios/roles quedan para una etapa multiusuario. |
| Datos sensibles | Se evita loguear direcciones completas o GPS exacto en evidencia estructurada futura. |
| Payloads malformados | Middleware canonico con limite 1 MiB y errores tipados en `/api/v1`. |
| Excepciones inseguras | Mapeo a respuestas seguras para errores conocidos. |
| Drift de dependencias | Versiones pinneadas en `pyproject.toml`, `uv.lock` y Docker. |
| Migraciones fallidas | Startup fail-closed y backup SQLite para DB existente. |
| Assets externos | Identificado como limite; se recomienda vendorizacion futura. |

El sistema no se presenta como produccion enterprise. La postura correcta es: MVP publicado, con riesgos identificados y mitigaciones razonables para el alcance.

## 14. Uso De IA En Co-Work

La IA se uso como colaborador durante el proceso, no como sustituto de criterio humano. El registro completo esta en `docs/ai-cowork-log.md`.

Usos principales:

- Interpretar feedback tecnico y convertirlo en tareas implementables.
- Crear PRD, arquitectura, epicas e historias con BMad.
- Implementar contratos, politicas, persistencia y pruebas.
- Dockerizar la aplicacion.
- Preparar documentacion tecnica, evidencia y artefactos de revision.
- Comparar opciones de deploy y publicacion.

Errores o limites observados:

- Algunos documentos heredados quedaron desactualizados respecto al estado real.
- La IA necesito verificacion real para no asumir que dependencias o SSH funcionaban.
- La publicacion y los links finales dependieron de acciones humanas.
- Las capturas y logs tenian que salir de una ejecucion real, no de una descripcion.

## 15. Reflexion Sobre Integracion De LLM O SLM Local

La integracion mas razonable de un LLM o SLM local seria como adaptador opcional de ANALYZE. Su funcion seria leer texto libre del incidente y proponer campos estructurados: categoria, prioridad, certificaciones, SLA y duracion estimada.

El modelo no deberia:

- Avanzar estados.
- Saltar reglas duras.
- Seleccionar tecnico final.
- Escribir memoria directamente.
- Inventar evidencia privada.

La salida del LLM/SLM tendria que pasar por los mismos contratos Pydantic. Si no valida, el sistema debe rechazarla como salida invalida de etapa.

Ventajas de un modelo local:

- Mayor privacidad.
- Posibilidad de demo offline.
- Menor dependencia de APIs cloud.
- Buen ajuste para prototipos con Ollama.

Limitaciones reales:

- Menor calidad que modelos cloud grandes en algunos casos.
- Dependencia de hardware local.
- Posible latencia superior.
- Necesidad de pruebas contra alucinaciones.
- Dificultad de mantenimiento y actualizacion del modelo.

Conclusion tecnica: el LLM/SLM debe ayudar a interpretar lenguaje natural, pero la autoridad operacional debe permanecer en reglas deterministicas, contratos, orquestador y evidencia persistida.

## 16. Despliegue Y Publicacion

El proyecto esta publicado en Render Free:

```text
https://smart-dispatch-q4xk.onrender.com
```

Tambien esta disponible en GitHub:

```text
https://github.com/rossanny25/smart-dispatch
```

Se agrego `render.yaml` para facilitar despliegue desde repositorio. El backend tambien acepta la variable `PORT`, comun en plataformas PaaS, y expone `/healthz` como endpoint de salud.

Limitacion del hosting gratuito:

- La instancia puede dormir por inactividad.
- La primera request puede demorar 50 segundos o mas.
- La persistencia runtime en hosting gratuito puede ser efimera.

Esto no invalida la publicacion del MVP, porque el proyecto conserva seeds reproducibles y Docker local como respaldo.

## 17. Limitaciones Del MVP

Limitaciones intencionales:

- No hay panel admin.
- No hay roles, registro de usuarios ni recuperacion de clave.
- La gestion de datos demo se hace por seeds JSON.
- La UI legacy todavia muestra algunas trazas descriptivas.
- No se implementa aprendizaje semantico completo de produccion.
- No se garantiza persistencia productiva en hosting gratuito.
- No se implementan integraciones reales con GPS, clima o trafico.

Estas limitaciones son coherentes con el objetivo: demostrar orquestacion, memoria persistente, explicabilidad y publicacion de un prototipo funcional.

## 18. Roadmap Recomendado

Prioridades futuras:

1. Agregar una demo guiada dentro de la interfaz: reset de escenario, seleccion de orden, despacho, aprobacion y cierre de servicio en un recorrido visible.
2. Mostrar reglas duras por tecnico antes del score: disponibilidad, certificaciones, turno, carga maxima, limite de conduccion y EPP requerido.
3. Separar visualmente score objetivo y confianza de recomendacion para evitar que el usuario confunda calidad de asignacion con calidad de evidencia.
4. Agregar un escenario `NO_FEASIBLE_CANDIDATES` donde ningun tecnico cumpla las restricciones, mostrando razones de descarte sin forzar recomendacion.
5. Mostrar en frontend los `DispatchRun` canonicos de `/api/v1`, incluyendo estados `CAPTURE`, `ANALYZE`, `PLAN`, `EVALUATE` y `WAIT_FOR_DECISION`.
6. Implementar decision humana y outcome completo sobre la API canonica para reemplazar gradualmente las rutas legacy de la UI.
7. Completar memoria episodica y promocion semantica con escenarios comparativos memoria on/off.
8. Mejorar accesibilidad WCAG: foco visible, labels semanticos, navegacion por teclado y mensajes de error legibles.
9. Evaluar Ollama como adaptador local opcional de `ANALYZE`, manteniendo validacion Pydantic y reglas deterministicas.
10. Expandir autenticacion solo si el sistema evoluciona a uso multiusuario.

## 19. Conclusiones

Smart Dispatch IA consolida una idea conceptual en una aplicacion real, publicada, ejecutable y documentada. El sistema ya no depende solo de una narrativa sobre agentes; ahora presenta una arquitectura tecnica con orquestacion deterministica, reglas duras, scoring, confianza, persistencia, pruebas, Docker, repositorio publico y evidencia de uso.

El aporte principal es mostrar como un sistema "agentico" puede mantenerse controlado. Los agentes producen evidencia, pero no gobiernan el estado. La memoria puede informar decisiones, pero no reemplaza restricciones de seguridad. La IA puede colaborar en el analisis, pero la aplicacion conserva mecanismos deterministas para que el resultado sea auditable.

Para su alcance actual, el proyecto demuestra madurez tecnica y conceptual: existe, funciona, esta publicado y deja una ruta clara de evolucion hacia un sistema mas completo.
