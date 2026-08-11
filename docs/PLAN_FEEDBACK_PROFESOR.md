# Plan de desarrollo basado en el feedback del profesor

## Objetivo

Convertir Smart Dispatch IA de una propuesta descriptiva a una especificación técnica demostrable, manteniendo el alcance de un prototipo educativo.

## Enfoque adoptado

El sistema será un **pipeline secuencial controlado por una máquina de estados determinista**:

`CAPTURAR -> ANALIZAR -> PLANIFICAR -> EVALUAR -> ESPERAR_DECISION -> APRENDER`

Los agentes producen y consumen JSON validable. El orquestador controla las transiciones, registra cada ejecución y evita que un agente omita restricciones de negocio.

## Prioridad 1 — Formalizar lo que decide el sistema

### Orquestación

- Implementar estados y transiciones explícitas.
- Registrar inicio, fin, duración, entrada y salida de cada agente.
- Definir rutas de error y el caso sin candidatos factibles.

### Reglas duras

Un técnico queda fuera del conjunto factible si:

- no está disponible;
- no posee todas las certificaciones requeridas;
- está fuera de turno;
- la asignación supera el máximo de jornada permitido.

Estas reglas se aplican antes del ranking y no pueden ser anuladas por aprendizaje.

### Función objetivo

Para cada técnico factible se calcula un puntaje normalizado:

`score = 0.35 * SLA + 0.25 * proximidad + 0.20 * balance_carga + 0.10 * calidad + 0.10 * memoria - penalizaciones`

Cada componente se expresa entre 0 y 100. Los pesos se guardan como configuración para poder probar escenarios distintos. La respuesta debe mostrar el desglose del puntaje para que la recomendación sea explicable.

## Prioridad 2 — Memoria persistente y aprendizaje controlado

Usar SQLite como memoria compartida por todos los agentes, separada en:

- **memoria episódica:** órdenes, propuestas, decisiones humanas, resultados y eventos;
- **memoria semántica:** preferencias y calibraciones derivadas de varios episodios.

Política inicial de actualización:

- una observación nueva aumenta evidencia, pero no crea una regla definitiva;
- la confianza crece con observaciones consistentes;
- las preferencias contradictorias reducen la confianza;
- se aplica decaimiento por antigüedad para que información vieja influya menos;
- solo se promociona un patrón a memoria semántica al alcanzar un mínimo de muestras.

El prototipo usa aprendizaje incremental basado en estadísticas, no fine-tuning. Esto evita presentar reglas heurísticas como si fueran entrenamiento de un modelo.

## Prioridad 3 — Incertidumbre, explicabilidad y evaluación

Cada recomendación debe incluir:

- puntaje total y desglose por criterio;
- restricciones comprobadas;
- nivel de confianza;
- calidad/frescura de los datos;
- advertencias por GPS, clima o tráfico;
- alternativas evaluadas y motivos de descarte.

La confianza no equivale al puntaje. Se calcula a partir de:

- disponibilidad y frescura de los datos;
- cantidad de evidencia histórica;
- diferencia entre el primer y segundo candidato;
- presencia de condiciones inciertas.

## KPIs del prototipo

- tiempo medio hasta asignación;
- porcentaje de SLA cumplido;
- tasa de reasignación manual;
- error absoluto medio del tiempo estimado;
- balance de carga entre técnicos;
- porcentaje de recomendaciones aceptadas;
- latencia total y por agente;
- First-Time Fix Rate, cuando se registre el resultado técnico.

## Entregas sugeridas con BMAD

### Entrega 1 — Especificación

- Actualizar PRD.
- Definir arquitectura y contratos JSON.
- Crear épicas e historias con criterios de aceptación.

### Entrega 2 — Núcleo implementable

- Orquestador por estados.
- Motor de restricciones y función objetivo.
- SQLite con migración de los datos JSON existentes.
- API de simulación con desglose y confianza.

### Entrega 3 — Evidencia académica

- Panel de KPIs.
- Pruebas de reglas duras y escenarios de incertidumbre.
- Comparación de asignaciones con y sin memoria.
- Documento de decisiones, límites y riesgos.

## Orden recomendado de los flujos BMAD

1. `bmad-document-project`
2. `bmad-prd`
3. `bmad-architecture`
4. `bmad-create-epics-and-stories`
5. `bmad-check-implementation-readiness`
6. `bmad-sprint-planning`
7. `bmad-dev-story`
8. `bmad-code-review`

Los flujos deben ejecutarse en tareas nuevas para mantener el contexto limpio.
