# Backlog de Tareas y Fases del Proyecto

Este documento detalla el backlog de desarrollo del proyecto Smart Dispatch IA, estructurado por fases operativas.

---

## Fase 1: Diseño Conceptual e Inicialización (Completado)
- [x] Crear e inicializar la estructura básica del repositorio de especificaciones.
- [x] Redactar los 14 archivos de especificaciones funcionales en `spec/`.
- [x] Desarrollar y validar los prompts para los 5 agentes en `prompts/`.
- [x] Crear el archivo de contexto general `docs/CONTEXT.md`.

## Fase 2: Implementación de la Simulación e Interfaz Gráfica (Fase Actual)
- [ ] Configurar el backend Express en Node.js para simular las respuestas de los agentes.
- [ ] Crear el motor del orquestador de agentes en el servidor.
- [ ] Inicializar el frontend SPA utilizando React y Vite.
- [ ] Diseñar el panel de despacho y el simulador interactivo de frenos/aceleradores.
- [ ] Implementar la consola visual para ver el paso a paso de los agentes con sus trazas de pensamiento.
- [ ] Configurar la persistencia local de la memoria en formato JSON.

## Fase 3: Integración de Modelos de Lenguaje y Producción (Fase Futura)
- [ ] Conectar los prompts a APIs reales de LLM (Gemini/OpenAI) con llaves API opcionales.
- [ ] Integrar base de datos relacional persistente (SQLite/PostgreSQL) y base de datos vectorial para embeddings de memoria semántica.
- [ ] Consolidar pruebas de rendimiento y latencia para cumplir con el SLA de respuesta menor a 3 segundos.
- [ ] Desplegar piloto en producción.