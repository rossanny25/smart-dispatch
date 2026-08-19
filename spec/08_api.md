# Especificación de API REST - Smart Dispatch IA

## Objetivo
Documentar los endpoints de la API del backend que facilitan la integración de datos y el flujo de comunicación entre la interfaz de usuario y el motor de agentes.

## Endpoints de la API

### 1. Gestión de Técnicos
* **GET `/api/technicians`**
  - **Descripción**: Obtiene la lista completa de técnicos, su disponibilidad, ubicación actual y certificaciones.
  - **Respuesta (200 OK)**:
    ```json
    [
      {
        "id": "tech_01",
        "name": "Sofía Torres",
        "status": "disponible",
        "current_location": { "lat": -34.6037, "lng": -58.3816, "zone": "Centro" },
        "certifications": ["Redes WAN", "Fibra Óptica"],
        "active_workload_hours": 3.5
      }
    ]
    ```

---

### 2. Gestión de Órdenes de Trabajo
* **GET `/api/orders`**
  - **Descripción**: Obtiene el listado histórico e incidentes activos pendientes de asignación.
  - **Respuesta (200 OK)**: Listado de órdenes de trabajo.
* **POST `/api/orders`**
  - **Descripción**: Crea una nueva orden de trabajo ingresada por el despachador.
  - **Cuerpo de Solicitud (JSON)**:
    ```json
    {
      "raw_text": "Fuga de gas en cocina principal de sucursal Palermo",
      "address": "Av. Santa Fe 3400, CABA"
    }
    ```

---

### 3. Simulación de Despacho (Motor Agéntico)
* **POST `/api/dispatch/simulate`**
  - **Descripción**: Dispara la ejecución secuencial del ciclo de agentes para analizar y recomendar asignaciones para una orden de trabajo específica.
  - **Cuerpo de Solicitud (JSON)**:
    ```json
    {
      "order_id": "order_102",
      "environment": {
        "weather": "lluvia_extrema", // soleado, lluvia_moderada, lluvia_extrema
        "traffic": "congestionado", // normal, congestionado
        "gps_signal": "online" // online, offline
      }
    }
    ```
  - **Respuesta (200 OK)**:
    ```json
    {
      "order_id": "order_102",
      "recommended_assignment": {
        "technician_id": "tech_01",
        "score": 85.0,
        "reasoning": "Recomendada por proximidad y certificación de redes, penalizada un 10% por congestión vial severa."
      },
      "agent_logs": {
        "capture": { "thought": "...", "output": {} },
        "analyze": { "thought": "...", "output": {} },
        "plan": { "thought": "...", "output": {} },
        "evaluate": { "thought": "...", "output": {} }
      }
    }
    ```

---

### 4. Confirmación de Asignación y Aprendizaje
* **POST `/api/dispatch/confirm`**
  - **Descripción**: Confirma la asignación de una orden a un técnico. Si el despachador cambia al técnico recomendado, se registra para el aprendizaje de preferencias.
  - **Cuerpo de Solicitud (JSON)**:
    ```json
    {
      "order_id": "order_102",
      "assigned_technician_id": "tech_02", // El usuario eligió al técnico 2 en vez del recomendado 1
      "feedback_comment": "Juan tiene más experiencia en Palermo aunque esté un poco más lejos."
    }
    ```
  - **Respuesta (200 OK)**:
    ```json
    {
      "status": "confirmado",
      "learning_registered": true
    }
    ```

---

### 5. Memoria de Aprendizaje
* **GET `/api/memory/learning`**
  - **Descripción**: Retorna la lista de coeficientes de calibración y preferencias aprendidas de la memoria semántica.
  - **Respuesta (200 OK)**:
    ```json
    [
      {
        "key": "preference_palermo_gas",
        "value": "Preferencia por técnico Juan Pérez para reparaciones de gas en zona Palermo basada en correcciones del despachador.",
        "confidence": 0.88
      }
    ]
    ```

## Checklist de API
- [x] Detallar endpoints, métodos y payloads de ejemplo.
- [ ] Implementar los controladores en Express.
- [ ] Validar la correcta respuesta de los endpoints mediante llamadas HTTP simuladas.
