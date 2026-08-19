# Agentes de IA - Smart Dispatch IA

## Objetivo
Describir detalladamente los roles, objetivos, entradas y salidas de los cinco agentes que conforman el ciclo de decisión inteligente de la aplicación.

## Los 5 Agentes del Sistema

```
+--------------------+
| 1. Capture Agent   | ---> Captura y estructura la solicitud inicial
+--------------------+
          |
+--------------------+
| 2. Analyze Agent   | ---> Clasifica, extrae habilidades y evalúa la urgencia
+--------------------+
          |
+--------------------+
| 3. Planning Agent  | ---> Calcula candidatos idóneos y asigna un puntaje
+--------------------+
          |
+--------------------+
| 4. Evaluation Agent| ---> Valida reglas de negocio, SLAs y restricciones
+--------------------+
          |
+--------------------+
| 5. Learning Agent  | ---> Procesa feedback y actualiza la memoria persistente
+--------------------+
```

---

### 1. Agente de Captura (Capture Agent)
* **Objetivo**: Tomar la información de entrada cruda (solicitudes en lenguaje natural enviadas por clientes o despachadores a través de formularios, chats, emails o transcripciones de voz) y estructurarla en un formato JSON estandarizado para el sistema.
* **Entradas**: Texto libre, geolocalización aproximada, adjuntos de imagen o audio (simulado).
* **Salidas**: JSON estructurado de la orden de trabajo (`titulo`, `descripcion`, `tipo_averia`, `cliente`, `direccion`).
* **Responsabilidad**: Normalizar campos incompletos y parsear descripciones informales a tipos estandarizados.

---

### 2. Agente Analizador (Analyze Agent)
* **Objetivo**: Evaluar la solicitud estructurada para determinar su criticidad, prioridad y las habilidades técnicas o certificaciones específicas requeridas para su ejecución.
* **Entradas**: JSON estructurado de la orden de trabajo.
* **Salidas**: Perfil de habilidades requeridas (`certificaciones`, `herramientas_necesarias`) y nivel de urgencia (`criticidad` 1 a 5).
* **Responsabilidad**: Cruzar el tipo de avería con el diccionario de certificaciones y prioridades del negocio.

---

### 3. Agente Planificador (Planning Agent)
* **Objetivo**: Generar las mejores alternativas de asignación. Cruza las necesidades de la orden (habilidades, criticidad, ubicación) con la base de datos de técnicos activos, considerando distancia por GPS, carga de trabajo acumulada y preferencias históricas almacenadas en la memoria persistente.
* **Entradas**: Perfil de requerimientos de la orden, estado actual de técnicos (ubicación, agenda, certificaciones), estado del clima/tráfico, y la memoria persistente.
* **Salidas**: Lista de técnicos candidatos recomendados ordenados por un puntaje ponderado de idoneidad, incluyendo una justificación analítica.
* **Responsabilidad**: Ejecutar algoritmos de ruteo/búsqueda y ponderación multicriterio.

---

### 4. Agente Evaluador (Evaluation Agent)
* **Objetivo**: Actuar como una compuerta de seguridad y cumplimiento normativo. Verifica que las propuestas del planificador cumplan estrictamente con las reglas de negocio, límites de horas extras, restricciones de seguridad y SLAs. Si detecta violaciones, puede rechazar una recomendación o aplicar penalizaciones.
* **Entradas**: Asignación propuesta, reglas de negocio activas, agenda laboral del técnico, restricciones operativas.
* **Salidas**: Estado de validación (`aprobado`/`rechazado`), lista de alertas y justificación de cumplimiento.
* **Responsabilidad**: Salvaguardar la seguridad del técnico y el cumplimiento de las políticas empresariales.

---

### 5. Agente de Aprendizaje (Learning Agent)
* **Objetivo**: Procesar la retroalimentación del despachador (ej. si aceptó o modificó la recomendación) y el resultado real en campo (ej. duración real del trabajo versus la estimada) para actualizar la memoria semántica persistente y mejorar las futuras planificaciones.
* **Entradas**: Recomendación inicial, decisión tomada por el despachador, reporte de finalización del técnico (duración, problemas), feedback del cliente.
* **Salidas**: Registro de aprendizaje (`lecciones_aprendidas`) que actualiza la base de conocimiento semántica de la memoria persistente.
* **Responsabilidad**: Analizar desvíos y registrar preferencias y heurísticas aprendidas.

---

## Checklist de Agentes
- [x] Detallar roles y responsabilidades individuales.
- [ ] Definir prompts específicos para cada agente en `prompts/`.
- [ ] Implementar la clase de simulación de agentes en el backend.
