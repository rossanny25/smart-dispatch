# Contexto del Proyecto - Smart Dispatch IA v2.0

Este documento sirve como referencia de contexto para que los agentes de IA comprendan el origen, estructura y estado de avance de la aplicación Smart Dispatch IA.

## Resumen del Proyecto
**Smart Dispatch IA** es un sistema inteligente diseñado para resolver el problema clásico del despacho y asignación de órdenes de trabajo en el área de servicios de campo (Field Service). El núcleo del sistema es un **Orquestador Cíclico** que coordina cinco agentes especializados y utiliza una **Memoria Persistente Semántica** para aprender de los resultados reales y de la interacción con los despachadores humanos.

## Estructura de Carpetas
- `spec/`: Documentación detallada y especificaciones de negocio de cada módulo del sistema (overview, problemas, reglas, arquitectura, modelo de datos, etc.).
- `prompts/`: Definición de los prompts del sistema y ejemplos de entrada y salida para cada uno de los 5 agentes de IA.
- `docs/`: Guías de contexto (`CONTEXT.md`) y listados de tareas históricas y pendientes (`TASKS.md`).
- `backend/`: Código de Node.js/Express que expone la API de simulación y el motor del ciclo de agentes.
- `frontend/`: Código en React + Vite que proporciona la interfaz visual premium para despachar órdenes y configurar simulaciones.

## Conceptos Clave
- **Ciclo OODA**: Observar (Capture Agent) -> Orientar (Analyze Agent) -> Decidir (Planning Agent) -> Actuar (Acción / Asignación recomendada) -> Evaluar (Evaluation Agent) -> Aprender (Learning Agent).
- **Frenos y Aceleradores**: Parámetros que modifican la toma de decisiones en tiempo real (clima, tráfico, señal GPS y feedback del usuario).
- **Memoria Semántica**: Base de conocimientos compartida que afina las estimaciones del planificador en función del histórico operacional y las preferencias aprendidas.