# Memoria Persistente - Smart Dispatch IA

## Objetivo
Explicar cómo funciona el sistema de almacenamiento de datos e historial y cómo la memoria semántica (aprendizaje continuo) influye en las futuras asignaciones para mejorar el rendimiento del despacho.

## Estructura de Memoria Híbrida
Para lograr un aprendizaje continuo, el sistema utiliza dos tipos de almacenamiento que integran la base de datos operativa y el repositorio de conocimiento del agente:

```
                  +-----------------------------------+
                  |         Smart Dispatch DB         |
                  +-----------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
|  Memoria Operacional  |                       |   Memoria Semántica   |
|   (BBDD Relacional)   |                       |    (Base de Aprendizaje)|
+-----------------------+                       +-----------------------+
| - Datos de Técnicos   |                       | - Preferencias del    |
| - Órdenes de Trabajo  |                       |   Despachador         |
| - Historial y Tiempos |                       | - Tiempos Reales Ajus.|
| - SLAs y Métricas     |                       | - Perfiles de Eficiencia|
+-----------------------+                       +-----------------------+
```

### 1. Memoria Operacional / Transaccional
Almacena el estado actual de la empresa. Es estructurada y consultable mediante consultas lógicas directas.
- **Técnicos**: Perfil básico, habilidades certificadas, posición de inicio, disponibilidad semanal.
- **Órdenes de Trabajo**: Registro de todas las solicitudes, su estado (pendiente, asignada, en viaje, completada, cancelada), prioridad y ubicación.
- **Trazas de Ejecución**: El log completo de cada ciclo de agentes (los resultados de Capture, Analyze, Plan y Evaluation) para fines de auditoría y análisis.

### 2. Memoria Semántica y de Aprendizaje (Persistent Agentic Memory)
Esta base almacena patrones de comportamiento, preferencias aprendidas y correcciones aplicadas por el despachador.
- **Ajustes de Tiempos Estimados**: Si la base de datos dice que una reparación de caldera toma 60 minutos, pero el histórico de la memoria registra que en promedio toma 85 minutos, el Agente Planificador utilizará 85 minutos para futuras estimaciones en lugar de la configuración estática.
- **Heurísticas de Técnico-Zona**: La memoria registra si un técnico tiene un desempeño sobresaliente en cierta zona geográfica o si tiene dificultades de traslado, adaptando su probabilidad de asignación en esa zona.
- **Preferencia del Despachador**: Si el planificador recomendó a Juan para un servicio de gas y el despachador lo cambió manualmente por Sofía porque "Juan suele tomar más tiempo en las explicaciones de seguridad", el Agente de Aprendizaje almacena este patrón. En la siguiente orden similar, priorizará a técnicos con el perfil de Sofía.
- **Desempeño Específico de Tareas (Skill Calibration)**: Calibra el tiempo medio de resolución de un técnico para tipos de trabajo particulares. Por ejemplo, "Carlos Rodríguez resuelve cortes de luz un 15% más rápido que la media de la empresa".

## Cómo Influye la Memoria en el Futuro
Cuando ingresa una nueva orden, el **Planning Agent** realiza una consulta de similitud histórica:
1. Busca órdenes similares del pasado en la memoria.
2. Analiza cuáles técnicos las resolvieron satisfactoriamente.
3. Recupera desvíos de tiempo e imprevistos climatológicos registrados en esa zona.
4. Ajusta los puntajes de asignación en consecuencia.

Esto crea un **bucle de retroalimentación positivo**: a mayor cantidad de órdenes completadas y feedback procesado, las asignaciones propuestas por la IA serán cada vez más acertadas, reduciendo la intervención manual del despachador.

## Checklist de Memoria
- [x] Detallar las categorías de almacenamiento (operacional y semántico).
- [x] Explicar la integración del feedback del usuario en la memoria.
- [ ] Implementar la persistencia de aprendizajes en un archivo `learning_store.json` en el backend.
- [ ] Renderizar el historial de aprendizajes acumulados en la UI.
