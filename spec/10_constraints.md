# Restricciones del Sistema - Smart Dispatch IA

## Objetivo
Enumerar las limitaciones técnicas, normativas y operativas que debe respetar el desarrollo del software para asegurar la viabilidad del proyecto.

## Restricciones Técnicas

### 1. Tiempo de Respuesta (Latencia)
- El proceso de orquestación agéntica completo (desde que el despachador envía el texto hasta que el planificador y evaluador retornan la propuesta) no debe superar los **3 segundos** de latencia total.
- Para lograr esto, se deben estructurar los prompts de manera eficiente y habilitar caches locales para consultas geográficas y metadatos estáticos de técnicos.

### 2. Límites de LLM y Control de Tokens
- El sistema debe estar diseñado para minimizar el consumo de tokens de entrada/salida.
- Los agentes Capture y Analyze deben usar esquemas de salida estricta (JSON schemas de LLM o técnicas de *Structured Outputs*) para evitar respuestas redundantes o mal formateadas que causen reintentos de red.

### 3. Privacidad y Seguridad de Datos (compliance)
- Toda dirección física de clientes y geolocalización en tiempo real de técnicos debe manejarse bajo cifrado HTTPS en tránsito.
- La geolocalización histórica no se almacena como coordenadas exactas en la memoria semántica a largo plazo; en su lugar, se agrupa a nivel de zonas o comunas para proteger la privacidad individual.

## Restricciones de Negocio y Operativas

### 4. Modo Desconectado (Falla de GPS / Red)
- En caso de caída de señal de red o de satélite de un técnico (Freno: Señal GPS Offline), el planificador no debe dejar de proponer soluciones. Debe aplicar una heurística de contingencia basada en su última ubicación registrada y penalizar la recomendación con una advertencia en la UI.

### 5. Prioridad de Seguridad Operativa
- Ninguna regla de balance de carga o ruteo de menor distancia puede anular las restricciones de seguridad:
  - Ningún técnico sin certificación de gas certificada puede tocar una caldera.
  - Ningún técnico puede exceder el límite de horas extras estipulado por el convenio de trabajo (ej. máximo 2 horas extras por día).

## Checklist de Restricciones
- [x] Detallar latencias deseadas y mitigaciones para LLM.
- [x] Definir restricciones de seguridad y privacidad.
- [ ] Implementar mecanismos de contingencia para la simulación offline en el backend.
