# Reglas de Negocio - Smart Dispatch IA

## Objetivo
Establecer las reglas lógicas, límites operativos, condiciones de seguridad y criterios de priorización que rigen el motor de despacho inteligente y que deben ser validadas por los agentes (especialmente el Agente Evaluador).

## Reglas Operativas del Despacho
1. **Disponibilidad Estricta**: No se puede asignar una orden de trabajo a un técnico que se encuentre ausente (licencia, enfermedad, vacaciones) o fuera de su jornada laboral programada.
2. **Cumplimiento de Horarios**: El tiempo de viaje estimado más la duración estimada del trabajo no debe exceder el horario de finalización del turno diario del técnico, a menos que se declare una emergencia crítica de nivel 5 y el técnico acepte horas extras.
3. **Certificación Obligatoria**: Ciertas categorías de órdenes de trabajo requieren certificaciones específicas para garantizar la seguridad y calidad:
   - *Trabajos de Gas*: Requieren certificación de "Gasista Matriculado".
   - *Trabajos Eléctricos de Alta Tensión*: Requieren certificación de "Técnico Electricista Categoría A".
   - *Climatización Industrial (HVAC)*: Requieren certificación en refrigerantes de alta presión.
   - *Instalación de Redes Fibra*: Requieren curso de seguridad en alturas.
4. **Priorización de Emergencias (SLA)**: Las órdenes de trabajo se clasifican según su criticidad. Una orden de emergencia (ej. fuga de gas, cortocircuito eléctrico, falla de servidor crítico) se antepone a mantenimientos programados e instalaciones nuevas, reprogramando automáticamente tareas no críticas si es necesario.
5. **Balance de Carga Laboral**: El planificador debe evitar la sobrecarga de un único técnico de forma consecutiva. La asignación debe priorizar a los técnicos calificados que tengan menor cantidad de horas asignadas en el día, promoviendo una distribución equitativa.
6. **Radio Geográfico Máximo**: Por cuestiones de costo y fatiga, no se recomienda asignar un técnico que se encuentre a más de 50 km de la orden, salvo que sea el único disponible con la certificación crítica requerida.

## Matriz de Prioridades de Órdenes
| Nivel | Criticidad | Descripción | SLA de Respuesta | Requiere Certificación Especial |
|---|---|---|---|---|
| Lvl 5 | Crítica / Emergencia | Riesgo de vida, fugas de gas, fuego, fallas masivas de energía. | < 1 Hora | Sí (Matriculados específicos) |
| Lvl 4 | Alta | Avería completa de servicio residencial o PyME. | < 4 Horas | Sí |
| Lvl 3 | Media | Degradación parcial de servicio, fallas menores no críticas. | < 12 Horas | Opcional según especialidad |
| Lvl 2 | Baja | Instalaciones nuevas planificadas. | < 48 Horas | No (Instalador básico) |
| Lvl 1 | Mantenimiento | Inspecciones preventivas anuales o rutinarias. | Programado | No |

## Límites Operativos y Condiciones de Seguridad
- **Horas de Conducción Máximas**: Ningún técnico puede conducir más de 4 horas totales acumuladas por jornada laboral.
- **Equipo de Protección Personal (EPP)**: Las tareas nivel 4 y 5 requieren la validación en el checklist de que el técnico cuenta con el kit de EPP correspondiente en su vehículo.

## Checklist de Reglas
- [x] Definir niveles de criticidad y SLAs correspondientes.
- [x] Establecer restricciones de certificación para gas y electricidad.
- [ ] Implementar validaciones lógicas de estas reglas en el backend del simulador (Agente Evaluador).
- [ ] Mostrar alertas de violación de reglas en la interfaz de usuario.
