# Modelo de Datos - Smart Dispatch IA

## Objetivo
Definir los esquemas de datos estructurados (JSON schemas) utilizados por la aplicación y los agentes para garantizar la consistencia en el intercambio de información y la persistencia en las bases de datos.

## Esquemas Principales

### 1. Perfil del Técnico (Technician)
Almacena el estado, habilidades e historial operativo de un técnico de servicio.
```json
{
  "id": "tech_01",
  "name": "Sofía Torres",
  "status": "disponible", // disponible, ocupado, ausente
  "current_location": {
    "lat": -34.6037,
    "lng": -58.3816,
    "zone": "Centro"
  },
  "certifications": ["Redes WAN", "Fibra Óptica", "Seguridad en Alturas"],
  "shift": {
    "start": "08:00",
    "end": "17:00"
  },
  "active_workload_hours": 3.5, // Horas de trabajo ya asignadas para hoy
  "rating": 4.8
}
```

### 2. Orden de Trabajo (Work Order)
Contiene la información de la solicitud de servicio y su nivel de criticidad.
```json
{
  "id": "order_102",
  "client": "Restaurante El Centro",
  "address": "Av. Corrientes 1250, CABA",
  "location": {
    "lat": -34.6041,
    "lng": -58.3820
  },
  "raw_text": "Urgente: Se cayó el enlace de internet secundario y la terminal de pago no conecta. No podemos facturar.",
  "status": "pendiente", // pendiente, asignada, en_viaje, completada, rechazada
  "structured_data": {
    "category": "Telecomunicaciones",
    "subcategory": "Falla de Enlace",
    "priority": 4, // 1 (Mantenimiento) a 5 (Emergencia Crítica)
    "required_skills": ["Redes WAN"]
  },
  "created_at": "2026-06-28T19:15:00Z"
}
```

### 3. Asignación Propuesta (Assignment Proposal)
Generada por el Agente Planificador y validada por el Evaluador.
```json
{
  "order_id": "order_102",
  "technician_id": "tech_01",
  "travel_time_minutes": 15,
  "estimated_duration_minutes": 60,
  "scheduled_start": "2026-06-28T19:30:00Z",
  "score": 92.5, // Puntaje de idoneidad calculado
  "reasoning": "Técnico certificado a menor distancia física (1.2 km). Historial óptimo de resolución de fallas de enlace en la zona Centro.",
  "validation": {
    "status": "aprobada", // aprobada, rechazada
    "alerts": []
  }
}
```

### 4. Registro de Ciclo de Agentes (Agent Execution Log)
Mantiene la trazabilidad cognitiva para la explicación al despachador.
```json
{
  "order_id": "order_102",
  "cycle_timestamp": "2026-06-28T19:15:10Z",
  "steps": {
    "capture": {
      "agent": "Capture Agent v2",
      "thought": "Extrayendo cliente y dirección. Identifico problema de conexión de red.",
      "output": { "client": "Restaurante El Centro", "address": "Av. Corrientes 1250, CABA" }
    },
    "analyze": {
      "agent": "Analyze Agent v2",
      "thought": "Pérdida de facturación indica impacto de negocio. Asigno criticidad Nivel 4 (Alta). Requiere habilidad 'Redes WAN'.",
      "output": { "priority": 4, "required_skills": ["Redes WAN"] }
    },
    "plan": {
      "agent": "Planning Agent v2",
      "thought": "Buscando técnicos calificados en la zona Centro. Sofía Torres está a 15 min de viaje y libre.",
      "output": { "recommended_tech_id": "tech_01", "score": 92.5 }
    },
    "evaluate": {
      "agent": "Evaluation Agent v2",
      "thought": "Verificando límites del turno de Sofía. Su turno termina a las 17:00, la tarea se completa a las 16:30. Aprobado.",
      "output": { "status": "aprobado", "violations": [] }
    },
    "learning": {
      "agent": "Learning Agent v2",
      "thought": "Esperando feedback del despachador y reporte de cierre técnico para actualizar memoria de tiempos de viaje en hora pico.",
      "output": { "status": "pendiente" }
    }
  }
}
```

### 5. Memoria Semántica (Persistent Learning Memory)
Registro de conocimientos específicos acumulados por el sistema.
```json
{
  "key": "tech_efficiency_tech_01_networks",
  "type": "productivity_calibration",
  "content": {
    "technician_id": "tech_01",
    "skill": "Redes WAN",
    "average_duration_modifier": 0.85, // Resuelve 15% más rápido que la media estándar
    "total_jobs_evaluated": 12
  },
  "confidence_score": 0.94,
  "updated_at": "2026-06-28T19:00:00Z"
}
```

## Checklist de Datos
- [x] Definir modelos JSON para técnicos, órdenes, propuestas y logs.
- [ ] Implementar validación de esquemas en el backend.
- [ ] Inicializar los datos semilla (`seed_data.json`) en base a estos esquemas.
