# Funcionalidades Futuras - Smart Dispatch IA

## Objetivo
Visualizar la evolución a largo plazo del sistema Smart Dispatch IA, sirviendo de guía para futuros desarrollos e iteraciones del producto una vez validado el prototipo básico.

## Lista de Módulos Planificados

### 1. Ruteo Dinámico y Planificación Multiparada (Planificación Diaria Completa)
- **Descripción**: En lugar de asignar órdenes de trabajo de forma reactiva (una a una), el planificador podrá diseñar agendas completas de 8 horas para todos los técnicos al inicio de la jornada laboral.
- **Detalle**: Utilizar algoritmos avanzados de optimización de rutas (como Vehicle Routing Problem con ventanas de tiempo - VRPTW) integrados con APIs de Google Maps o Waze para optimizar el recorrido secuencial.

### 2. Notificaciones Proactivas al Cliente vía WhatsApp / SMS
- **Descripción**: Mantener informado al cliente sobre el estado de su servicio en tiempo real.
- **Detalle**: Cuando el técnico cambia su estado a "En Viaje", el sistema envía un mensaje automatizado con un link de seguimiento interactivo donde el cliente puede ver el desplazamiento del vehículo y la hora estimada de arribo (ETA) corregida por el tráfico en tiempo real.

### 3. Integración con Inventario de Repuestos (Spare Parts Management)
- **Descripción**: Evitar visitas fallidas por falta de repuestos.
- **Detalle**: Cruzar la orden de trabajo con el stock disponible en el vehículo asignado. Si la reparación requiere una válvula de gas específica, el Agente Evaluador rechazará al técnico que esté más cerca si este no cuenta con el repuesto en su inventario móvil, prefiriendo al técnico que sí lo tenga disponible.

### 4. Despacho por Voz (Speech-to-Dispatch)
- **Descripción**: Permitir al despachador ingresar órdenes mediante dictado de voz.
- **Detalle**: Incorporar modelos de transcripción (Speech-to-Text) en la UI que capturen la conversación telefónica con el cliente final y alimenten de forma automática al Capture Agent.

### 5. Algoritmos de Predicción de Deserción y Mantenimiento Predictivo
- **Descripción**: Anticipar la falla antes de que ocurra la orden de trabajo.
- **Detalle**: Analizar los datos históricos de los clientes para programar inspecciones periódicas de manera automática antes de que el cliente reporte una avería crítica.

## Checklist de Futuras Funcionalidades
- [x] Enumerar integraciones con sistemas externos (inventario, mapas).
- [x] Detallar mejoras en la comunicación con el usuario y cliente final.
- [ ] Documentar puntos de extensión en la arquitectura del backend para facilitar estas adiciones.
