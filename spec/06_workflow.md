# Flujo de Trabajo y Orquestación - Smart Dispatch IA

## Objetivo
Describir la secuencia cíclica de ejecución de los agentes autónomos coordinados por el orquestador central desde el ingreso de una orden hasta la consolidación del aprendizaje.

## Ciclo de Decisión Agéntico
El orquestador central coordina a los agentes siguiendo un proceso circular inspirado en el ciclo OODA (Observar, Orientar, Decidir, Actuar) adaptado para sistemas de IA:

```
            +-----------------------------------+
            |     1. Observación (Captura)      |
            +-----------------------------------+
                              |
                              v
            +-----------------------------------+
            |       2. Análisis (Triaje)        |
            +-----------------------------------+
                              |
                              v
            +-----------------------------------+
            |   3. Planificación (Asignación)   |
            +-----------------------------------+
                              |
                              v
            +-----------------------------------+
            |      4. Acción (Recomendación)    |
            +-----------------------------------+
                              |
                              v
            +-----------------------------------+
            |      5. Evaluación (Seguridad)    |
            +-----------------------------------+
                              |
                              v
            +-----------------------------------+
            |      6. Aprendizaje (Memoria)     |
            +-----------------------------------+
                              |
                              +---------> [Nueva Observación]
```

---

## Detalle de Pasos del Ciclo

### Paso 1: Observación (Agente de Captura)
- **Acción**: Recepción de una nueva orden de trabajo sin estructurar.
- **Proceso**: El sistema lee el mensaje (ej. *"Se cayó el internet en la sucursal Centro, no podemos facturar, urgente"*). Estructura el cliente, zona geográfica y descripción.

### Paso 2: Análisis (Agente Analizador)
- **Acción**: Categorización y priorización.
- **Proceso**: Se clasifica el tipo de avería (*Telecomunicaciones / Caída de Enlace*), la criticidad (*Nivel 4 - Alta por impacto en facturación*) y las habilidades requeridas (*Certificación Fibra / Redes WAN*).

### Paso 3: Planificación (Agente Planificador)
- **Acción**: Generación y puntuación de candidatos.
- **Proceso**: El agente lee la ubicación del incidente, consulta los técnicos activos que posean la certificación *Redes WAN*, extrae de la **Memoria Semántica** quién tiene el mejor tiempo histórico en esa sucursal, y calcula el tiempo de viaje y la carga laboral. Asigna un puntaje de idoneidad (0 a 100) a cada candidato calificado.

### Paso 4: Acción / Recomendación (Visualización en UI)
- **Acción**: Presentación al despachador.
- **Proceso**: Se le muestra al usuario la opción recomendada: *"Asignar a Sofía Torres: se encuentra a 15 min, está certificada en Redes WAN y tiene un 95% de tasa de éxito en la sucursal Centro. Hora de llegada estimada: 10:45 AM"*.

### Paso 5: Evaluación (Agente Evaluador)
- **Acción**: Validación de cumplimiento.
- **Proceso**: El agente verifica: ¿Sofía tiene equipo de seguridad para trabajos en altura? ¿Esta asignación viola su límite de jornada laboral (termina a las 11:00 AM)? Si todo se cumple, la asignación es marcada como **Segura**. Si no, emite una alerta preventiva.

### Paso 6: Aprendizaje (Agente de Aprendizaje)
- **Acción**: Procesamiento de feedback y cierre del bucle.
- **Proceso**: Ocurre en dos momentos:
  - **Inmediato**: El despachador aprueba la recomendación de Sofía o la rechaza para elegir a otro. Si la rechaza, el agente pregunta o analiza la causa para guardarla en memoria.
  - **A posteriori**: Cuando el trabajo finaliza en campo, se registran los datos reales de duración de viaje y resolución. Si Sofía demoró 50 minutos en lugar de los 30 estimados, se reporta a la memoria semántica para calibrar futuros estimados de Sofía en esa tarea.

---

## Checklist del Workflow
- [x] Detallar las etapas del ciclo OODA adaptado.
- [x] Definir las entradas y transiciones de estado de cada paso.
- [ ] Implementar la barra de progreso animada del ciclo en el frontend.
- [ ] Implementar las transiciones de estado en la API del backend.
