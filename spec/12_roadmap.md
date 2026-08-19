# Hoja de Ruta (Roadmap) - Smart Dispatch IA

## Objetivo
Definir los hitos principales y cronograma del proyecto Smart Dispatch IA para estructurar el desarrollo incremental de la aplicación.

## Cronograma por Fases

```
Fase 1: Diseño Conceptual (100%)
[======]
  |
  v
Fase 2: Prototipado y Simulación (Fase Actual)
[======]
  |
  v
Fase 3: Integración de Sistemas y LLM Real
[====]
  |
  v
Fase 4: Despliegue y Pruebas en Campo
[===]
```

---

### Fase 1: Diseño Funcional y Especificaciones (Completado)
- **Hitos**:
  - Redacción de los 14 archivos de especificaciones (`spec/*.md`).
  - Creación de prompts para los agentes Capture, Analyze, Planning, Evaluation y Learning (`prompts/*.md`).
  - Definición del modelo conceptual del ciclo de agentes.

### Fase 2: Prototipo Interactivo y Simulación (Fase Actual)
- **Hitos**:
  - Creación de la arquitectura del repositorio (Backend Express + Frontend React).
  - Implementación del simulador de agentes local con trazas de razonamiento.
  - Creación del dashboard premium en modo oscuro con visualización animada del ciclo.
  - Implementación interactiva de frenos y aceleradores (clima, tráfico, señal).
  - Persistencia de aprendizajes en almacenamiento JSON local.

### Fase 3: Integración y Robustez (Siguiente Paso)
- **Hitos**:
  - Conectar los prompts a APIs reales de modelos de lenguaje (OpenAI GPT-4o / Gemini 1.5 Pro).
  - Reemplazar el almacenamiento local por bases de datos robustas (PostgreSQL para transaccional y pgvector para memoria semántica).
  - Integración básica con APIs de geolocalización (Mapbox o Leaflet con datos reales).

### Fase 4: Pilotaje y Despliegue en Campo
- **Hitos**:
  - Desarrollo de una aplicación móvil simplificada para el técnico (recepción de tareas).
  - Implementación de un grupo piloto con 5 despachadores y 20 técnicos activos.
  - Medición de métricas de negocio clave: tasa de resolución en primera visita, tiempos de respuesta de SLA y satisfacción del cliente (CSAT).

## Checklist del Roadmap
- [x] Detallar las fases del proyecto con hitos clave.
- [ ] Completar el desarrollo de la Fase 2 en este espacio de trabajo.
- [ ] Documentar instrucciones para la transición a la Fase 3.
