from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "Smart_Dispatch_IA_Informe_Final.pdf"
DOCS_OUTPUT = ROOT / "docs" / "Smart_Dispatch_IA_Informe_Final.pdf"
EVIDENCE = ROOT / "docs" / "evidence"


def stylesheet():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleCenter",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=28,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubtitleCenter",
            parent=styles["BodyText"],
            alignment=TA_CENTER,
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#374151"),
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1Custom",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#111827"),
            spaceBefore=8,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2Custom",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1F2937"),
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyCustom",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            alignment=TA_LEFT,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallCustom",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#4B5563"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Caption",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#374151"),
            spaceBefore=4,
            spaceAfter=8,
        )
    )
    return styles


def p(text: str, styles):
    return Paragraph(text, styles["BodyCustom"])


def h1(text: str, styles):
    return Paragraph(text, styles["H1Custom"])


def h2(text: str, styles):
    return Paragraph(text, styles["H2Custom"])


def bullet(items: list[str], styles):
    return ListFlowable(
        [ListItem(Paragraph(item, styles["BodyCustom"])) for item in items],
        bulletType="bullet",
        leftIndent=18,
    )


def table(data: list[list[str]], widths: list[float] | None = None):
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def image(path: Path, max_width: float, max_height: float, styles, caption: str):
    with PILImage.open(path) as im:
        width, height = im.size
    scale = min(max_width / width, max_height / height)
    return KeepTogether(
        [
            Image(str(path), width=width * scale, height=height * scale),
            Paragraph(caption, styles["Caption"]),
        ]
    )


def pre(text: str):
    return Preformatted(
        text,
        ParagraphStyle(
            "Code",
            fontName="Courier",
            fontSize=7.2,
            leading=9,
            textColor=colors.HexColor("#111827"),
            backColor=colors.HexColor("#F3F4F6"),
            leftIndent=4,
            rightIndent=4,
            spaceBefore=4,
            spaceAfter=8,
        ),
    )


def architecture_ascii():
    return """Despachador
  -> Browser UI
  -> FastAPI HTTP Adapter (/api/v1 y /api)
  -> Application Commands
  -> DispatchOrchestrator
  -> Domain Policies (eligibility, scoring, confidence)
  -> Unit Of Work / SQLite Repositories
  -> SQLite (runs, snapshots, stages, transitions)"""


def state_ascii():
    return """[*] -> CAPTURE -> ANALYZE -> PLAN -> EVALUATE
EVALUATE -> WAIT_FOR_DECISION
EVALUATE -> NO_FEASIBLE_CANDIDATES
CAPTURE/ANALYZE/PLAN/EVALUATE -> FAILED"""


def uml_ascii():
    return """WorkOrder 1 -> many DispatchRun
DispatchRun 1 -> many RunSnapshot
DispatchRun 1 -> many StageExecution
DispatchRun 1 -> many StateTransition
DispatchRun 1 -> many EligibilityCandidate
EligibilityCandidate 0..1 -> 0..1 ScoredTechnician
ScoredTechnician 0..1 -> 0..1 ConfidenceOutput
Technician 1 -> many EligibilityCandidate"""


def build_story(styles):
    story = []

    story.append(Paragraph("Smart Dispatch IA", styles["TitleCenter"]))
    story.append(Paragraph("Informe Final - Orquestacion Agentica Ciclica y Memoria Persistente", styles["SubtitleCenter"]))
    story.append(
        table(
            [
                ["Recurso", "Link"],
                ["Aplicacion en vivo", "https://smart-dispatch-q4xk.onrender.com"],
                ["Repositorio GitHub", "https://github.com/rossanny25/smart-dispatch"],
                ["Demo Docker local", "http://127.0.0.1:8050"],
                ["Acceso demo", "Usuario tecnico-fisca / clave smart2026AI"],
                ["Guia de ejecucion", "docs/runbook.md"],
                ["Evidencia de sesion", "docs/usage-session-log.md"],
            ],
            [1.8 * inch, 4.6 * inch],
        )
    )
    story.append(Spacer(1, 12))
    story.append(
        p(
            "Nota: la aplicacion publicada usa Render Free. Si la instancia estuvo inactiva, la primera carga puede demorar cerca de 50 segundos o mas mientras el servicio despierta.",
            styles,
        )
    )
    story.append(h1("Checklist de validacion", styles))
    story.append(
        table(
            [
                ["Requisito del proyecto", "Estado", "Evidencia"],
                ["Aplicacion real funcionando", "Cumplido", "Demo en Render y Docker local"],
                ["Links en primera pagina", "Cumplido", "Tabla inicial"],
                ["Arquitectura y UML", "Cumplido", "Diagramas incluidos"],
                ["Tecnologias justificadas", "Cumplido", "Tabla tecnica"],
                ["Capturas y log real", "Cumplido", "Secciones 9 y 10"],
                ["UX/UI Nielsen", "Cumplido", "Seccion 11"],
                ["Ciberseguridad", "Cumplido", "Seccion 12"],
                ["Uso de IA y reflexion LLM/SLM", "Cumplido", "Secciones 13 y 14"],
            ],
            [2.25 * inch, 1.0 * inch, 3.15 * inch],
        )
    )
    story.append(PageBreak())

    story.append(h1("1. Resumen ejecutivo", styles))
    story.append(
        p(
            "Smart Dispatch IA es un prototipo funcional de asistencia al despacho tecnico en servicios de campo. El proyecto convierte un modelo conceptual de orquestacion agentica y memoria persistente en una aplicacion web publicada, ejecutable con Docker y documentada con evidencia tecnica reproducible.",
            styles,
        )
    )
    story.append(
        p(
            "El sistema ayuda a decidir que tecnico conviene asignar a una orden de trabajo. Para hacerlo, separa el problema en etapas: captura de informacion, analisis de requerimientos, planificacion, evaluacion de restricciones, scoring, confianza y aprendizaje. La aplicacion no reemplaza al despachador: funciona como soporte a la decision y conserva evidencia de por que se recomienda un tecnico.",
            styles,
        )
    )
    story.append(
        p(
            "La evolucion principal frente al trabajo teorico inicial es que la orquestacion deja de ser una descripcion general y pasa a estar formalizada como una maquina de estados deterministica. Las reglas duras se aplican antes del ranking, la funcion objetivo esta versionada, la confianza se calcula separada del puntaje y la memoria persistente queda tratada como evidencia controlada.",
            styles,
        )
    )

    story.append(h1("2. Contexto y problema", styles))
    story.append(
        p(
            "En operaciones de campo, un despachador suele asignar tecnicos con informacion incompleta: tipo de incidente, zona, urgencia, habilidades requeridas, disponibilidad, carga de trabajo, distancia, clima, trafico y experiencia historica. Una mala asignacion puede causar demoras, incumplimiento de SLA, sobrecarga de tecnicos o decisiones poco explicables.",
            styles,
        )
    )
    story.append(
        p(
            "El problema no es solo seleccionar el tecnico mas cercano. Tambien hay restricciones que no deberian negociarse: disponibilidad, certificaciones, turno, jornada maxima, limite de conduccion y elementos de seguridad. Por eso el sistema primero determina factibilidad, luego rankea candidatos y finalmente expone evidencia para que el humano decida.",
            styles,
        )
    )

    story.append(h1("3. Evolucion desde el trabajo de medio ciclo", styles))
    story.append(
        table(
            [
                ["Observacion del feedback", "Evolucion implementada"],
                ["Orquestador ambiguo", "Maquina de estados deterministica controlada por DispatchOrchestrator."],
                ["Memoria persistente poco formalizada", "Separacion entre seeds, runtime SQLite y memoria de aprendizaje legacy."],
                ["Funcion objetivo descriptiva", "Scoring con componentes, pesos, penalizaciones y version de configuracion."],
                ["Aprendizaje generico", "Aprendizaje incremental/evidencial, sin prometer fine-tuning."],
                ["Falta de metricas concretas", "KPIs y evidencia requerida documentados para evaluacion futura."],
                ["Incertidumbre incompleta", "Confianza independiente, warnings y explicaciones estructuradas."],
                ["Falta de app real", "Render, Docker, screenshots, API evidence y logs reales."],
            ],
            [2.7 * inch, 3.7 * inch],
        )
    )
    story.append(PageBreak())

    story.append(h1("4. Arquitectura general", styles))
    story.append(
        p(
            "La arquitectura objetivo es un monolito modular hexagonal con pipeline deterministico. Se eligio monorepo porque el frontend es estatico y FastAPI puede servir API y UI desde el mismo proceso. Esto reduce friccion operativa: un repositorio, un README, un comando Docker y una ruta clara de despliegue.",
            styles,
        )
    )
    story.append(pre(architecture_ascii()))
    story.append(
        bullet(
            [
                "frontend/: interfaz HTML, CSS y JavaScript vanilla.",
                "app/api/v1: API canonica versionada.",
                "app/application: comandos y casos de uso.",
                "app/domain: politicas puras de negocio.",
                "app/adapters: persistencia, legacy API y etapas deterministicas.",
                "data/seeds: datos reproducibles de demo.",
                "docs: informe, diagramas, evidencia y runbook.",
            ],
            styles,
        )
    )

    story.append(h1("5. Orquestacion agentica ciclica", styles))
    story.append(
        p(
            "El sistema modela el ciclo de despacho como una secuencia de estados. La pieza central es DispatchOrchestrator: los agentes no pueden avanzar estados por su cuenta. Esto reemplaza el orquestador ambiguo por un mecanismo auditable.",
            styles,
        )
    )
    story.append(pre(state_ascii()))
    story.append(
        table(
            [
                ["Etapa", "Responsabilidad"],
                ["CAPTURE", "Normaliza y valida la informacion de entrada."],
                ["ANALYZE", "Deriva categoria, prioridad, SLA, certificaciones y duracion estimada."],
                ["PLAN", "Aplica reglas duras y calcula ranking solo para candidatos elegibles."],
                ["EVALUATE", "Agrega confianza, advertencias y explicacion sin cambiar el ranking."],
                ["WAIT_FOR_DECISION", "Espera la decision humana del despachador."],
            ],
            [1.5 * inch, 4.9 * inch],
        )
    )
    story.append(PageBreak())

    story.append(h1("6. UML principal", styles))
    story.append(pre(uml_ascii()))
    story.append(
        p(
            "El modelo conserva la separacion entre orden, corrida de despacho, snapshots, ejecuciones por etapa, transiciones de estado, candidatos elegibles, puntajes y salida de confianza. Esta separacion permite explicar cada recomendacion sin mezclar reglas duras, scoring y memoria.",
            styles,
        )
    )

    story.append(h1("7. Tecnologias usadas", styles))
    story.append(
        table(
            [
                ["Tecnologia", "Uso", "Justificacion"],
                ["Python 3.12", "Backend principal", "Lenguaje claro y buen ecosistema web/testing."],
                ["FastAPI", "API HTTP", "Contratos claros, OpenAPI y soporte ASGI."],
                ["Pydantic v2", "Validacion", "Modelos estrictos y rechazo de campos desconocidos."],
                ["SQLAlchemy Core", "Persistencia", "SQL explicito sin acoplar dominio a ORM."],
                ["Alembic", "Migraciones", "Control de evolucion del esquema SQLite."],
                ["SQLite", "Base local", "Suficiente para un MVP single-user y despliegues livianos."],
                ["HTML/CSS/JS", "Frontend", "Interfaz simple, auditable y sin build complejo."],
                ["Docker/Compose", "Ejecucion", "Reproducibilidad local y deploy con Dockerfile."],
                ["Render Free", "Publicacion", "Link publico evaluable."],
                ["pytest", "Verificacion", "Pruebas unitarias, integracion y contrato."],
                ["BMad Method", "Especificacion", "PRD, arquitectura, epicas, historias y trazabilidad."],
            ],
            [1.35 * inch, 1.45 * inch, 3.6 * inch],
        )
    )
    story.append(PageBreak())

    story.append(h1("8. Reglas duras, scoring y memoria", styles))
    story.append(
        p(
            "El prototipo distingue entre restricciones duras y criterios de optimizacion. Un tecnico que falla una restriccion dura no puede recibir puntaje objetivo. Esta decision evita que una puntuacion alta o una preferencia aprendida oculte una violacion operativa.",
            styles,
        )
    )
    story.append(bullet(["Tecnico disponible.", "Certificaciones requeridas.", "Turno vigente.", "Jornada maxima.", "Limite de conduccion.", "EPP requerido."], styles))
    story.append(pre("score = 0.35*SLA + 0.25*proximidad + 0.20*balance_carga + 0.10*calidad + 0.10*memoria - penalizaciones"))
    story.append(
        bullet(
            [
                "Tecnicos demo: data/seeds/technicians.json.",
                "Ordenes demo: data/seeds/orders.json.",
                "Memoria inicial: data/learning_store.json.",
                "Runtime SQLite local: data/smart_dispatch.db.",
                "Runtime Docker: volumen smart_dispatch_data.",
                "Reset operativo: POST /api/reset o docker compose down -v.",
                "Acceso demo: usuario tecnico-fisca, clave smart2026AI.",
            ],
            styles,
        )
    )
    story.append(
        p(
            "El sistema incluye login single-user para proteger la UI y las rutas API con cookie de sesion firmada. No incluye panel de administracion ni roles: la carga de informacion se realiza por seeds JSON versionados y por el flujo de aprendizaje del simulador.",
            styles,
        )
    )

    story.append(PageBreak())
    story.append(h1("9. Capturas del frontend", styles))
    screenshots = [
        ("01-dashboard-full.png", "Figura 1. Dashboard inicial con ordenes, tecnicos y controles de contexto."),
        ("02-dispatch-result.png", "Figura 2. Resultado de simulacion con ciclo agentico y recomendacion."),
        ("03-recommendation-approved.png", "Figura 3. Aprobacion de recomendacion y modal de cierre."),
        ("04-learning-completed.png", "Figura 4. Orden completada y aprendizaje registrado."),
    ]
    for filename, caption in screenshots:
        story.append(image(EVIDENCE / filename, 6.5 * inch, 6.4 * inch, styles, caption))
        story.append(PageBreak())

    story.append(h1("10. Log de sesion real", styles))
    story.append(
        table(
            [
                ["Campo", "Valor"],
                ["Fecha", "2026-08-11"],
                ["Runtime", "Docker Compose"],
                ["URL", "http://127.0.0.1:8050"],
                ["Comando", "docker compose up --build"],
                ["Objetivo", "Demostrar que la aplicacion existe, corre y sirve frontend/API."],
            ],
            [1.6 * inch, 4.8 * inch],
        )
    )
    story.append(
        bullet(
            [
                "Se inicio la aplicacion Dockerizada.",
                "Se abrio el frontend y se verifico /api/technicians.",
                "Se ejecuto una simulacion de despacho.",
                "Se aprobo la recomendacion.",
                "Se completo el servicio y se registro aprendizaje.",
                "Se exportaron logs Docker/Uvicorn.",
            ],
            styles,
        )
    )
    story.append(
        p(
            "Resultado observado: orden Cafeteria Martinez Belgrano, categoria Electricidad, prioridad 4, tecnico recomendado Juan Perez, score visible 98, viaje 8 minutos, duracion estimada 90 minutos y estado final completada.",
            styles,
        )
    )
    story.append(pre("Uvicorn running on http://0.0.0.0:8050\nGET / HTTP/1.1 200 OK\nGET /api/technicians HTTP/1.1 200 OK\nGET /api/orders HTTP/1.1 200 OK\nPOST /api/dispatch/simulate HTTP/1.1 200 OK\nPOST /api/dispatch/confirm HTTP/1.1 200 OK"))

    story.append(h1("11. Autoevaluacion UX/UI con Nielsen", styles))
    story.append(
        table(
            [
                ["Heuristica", "Evaluacion", "Mejora"],
                ["Visibilidad del estado", "Buena: etapas y recomendacion visibles.", "Mostrar estado canonico DispatchRun."],
                ["Relacion con el mundo real", "Buena: orden, tecnico, zona y prioridad.", "Etiquetar SLA, reglas duras y confianza."],
                ["Control del usuario", "Media: permite aprobar/cambiar.", "Agregar decision canonica completa."],
                ["Consistencia", "Buena: paneles y estados uniformes.", "Unificar errores API en frontend."],
                ["Prevencion de errores", "Media: backend valida mas que UI.", "Validar antes de enviar."],
                ["Reconocimiento", "Buena: ordenes y tecnicos visibles.", "Mantener contexto seleccionado."],
                ["Recuperacion de errores", "Media: API tiene errores tipados.", "Mostrar retry y explicacion no factible."],
                ["Ayuda/documentacion", "Buena: README, runbook e informe.", "Agregar panel breve dentro de la app."],
            ],
            [1.65 * inch, 2.35 * inch, 2.4 * inch],
        )
    )
    story.append(PageBreak())

    story.append(h1("12. Log de ciberseguridad", styles))
    story.append(
        table(
            [
                ["Riesgo", "Mitigacion actual", "Pendiente"],
                ["Exposicion accidental", "Default local 127.0.0.1; Docker explicito en 8050; login single-user.", "HTTPS y politicas de red."],
                ["Credencial compartida", "Cookie firmada y credencial configurable por entorno.", "Usuarios, roles, auditoria y CSRF antes de uso multiusuario."],
                ["Datos sensibles", "Evidencia demo y recomendacion por zona.", "Politica para datos reales."],
                ["JSON malformado/grande", "/api/v1 limita 1 MiB y usa errores tipados.", "Migrar rutas legacy restantes."],
                ["Excepciones inseguras", "Errores conocidos se mapean a respuestas estables.", "Politica productiva completa."],
                ["Drift de dependencias", "pyproject.toml, uv.lock y Docker pinnean dependencias.", "Escaneo de vulnerabilidades."],
                ["Migraciones fallidas", "Startup fail-closed y backups SQLite.", "Retencion/exportacion productiva."],
                ["Assets externos", "Aceptable en prototipo.", "Vendorizacion futura."],
            ],
            [1.65 * inch, 2.55 * inch, 2.2 * inch],
        )
    )

    story.append(h1("13. Uso de IA en co-work", styles))
    story.append(
        bullet(
            [
                "Interpretar feedback tecnico y convertirlo en tareas implementables.",
                "Crear PRD, arquitectura, epicas e historias con BMad.",
                "Implementar contratos, politicas, persistencia y pruebas.",
                "Dockerizar la aplicacion.",
                "Preparar documentacion tecnica, evidencia y artefactos de revision.",
                "Comparar opciones de deploy y publicacion.",
            ],
            styles,
        )
    )
    story.append(
        p(
            "La IA tambien tuvo limites: necesito verificacion real para no asumir que dependencias, Docker o SSH funcionaban; la publicacion final dependio de acciones humanas; y las capturas/logs tenian que salir de una ejecucion real, no de una descripcion.",
            styles,
        )
    )

    story.append(h1("14. Reflexion sobre integracion de LLM o SLM local", styles))
    story.append(
        p(
            "La integracion mas razonable de un LLM o SLM local seria como adaptador opcional de ANALYZE. Su funcion seria leer texto libre del incidente y proponer campos estructurados: categoria, prioridad, certificaciones, SLA y duracion estimada.",
            styles,
        )
    )
    story.append(
        bullet(
            [
                "No deberia avanzar estados, saltar reglas duras, seleccionar tecnico final, escribir memoria directamente ni inventar evidencia.",
                "Su salida deberia pasar por contratos Pydantic. Si no valida, el sistema debe rechazarla como salida invalida de etapa.",
                "Ventajas: privacidad, demo offline, menor dependencia cloud y buen ajuste para Ollama.",
                "Limitaciones: menor calidad potencial, dependencia de hardware, latencia, pruebas contra alucinaciones y mantenimiento.",
            ],
            styles,
        )
    )
    story.append(PageBreak())

    story.append(h1("15. Despliegue, roadmap y conclusiones", styles))
    story.append(
        p(
            "La aplicacion esta publicada en https://smart-dispatch-q4xk.onrender.com y el repositorio esta en https://github.com/rossanny25/smart-dispatch. Localmente se ejecuta con docker compose up --build y se abre en http://127.0.0.1:8050.",
            styles,
        )
    )
    story.append(
        bullet(
            [
                "No hay login ni roles.",
                "No hay panel admin.",
                "La gestion de datos demo se hace por seeds JSON.",
                "La UI legacy todavia muestra algunas trazas descriptivas.",
                "No se implementa aprendizaje semantico completo de produccion.",
                "No se garantiza persistencia productiva en hosting gratuito.",
                "No se implementan integraciones reales con GPS, clima o trafico.",
            ],
            styles,
        )
    )
    story.append(
        p(
            "Roadmap recomendado: demo guiada dentro de la interfaz; reglas duras visibles por tecnico antes del score; score objetivo y confianza separados; escenario NO_FEASIBLE_CANDIDATES sin recomendacion forzada; estados canonicos DispatchRun visibles en frontend; decision humana y outcome sobre /api/v1; memoria episodica con comparativas memoria on/off; accesibilidad WCAG; Ollama como adaptador local opcional; autenticacion solo si evoluciona a uso multiusuario.",
            styles,
        )
    )
    story.append(
        p(
            "Smart Dispatch IA consolida una idea conceptual en una aplicacion real, publicada, ejecutable y documentada. El sistema presenta orquestacion deterministica, reglas duras, scoring, confianza, persistencia, pruebas, Docker, repositorio publico y evidencia de uso.",
            styles,
        )
    )
    story.append(
        p(
            "El aporte principal es mostrar como un sistema agentico puede mantenerse controlado. Los agentes producen evidencia, pero no gobiernan el estado. La memoria puede informar decisiones, pero no reemplaza restricciones de seguridad. La IA puede colaborar en el analisis, pero la aplicacion conserva mecanismos deterministas para que el resultado sea auditable.",
            styles,
        )
    )
    return story


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(doc.leftMargin, 0.35 * inch, "Smart Dispatch IA - Informe Final")
    canvas.drawRightString(letter[0] - doc.rightMargin, 0.35 * inch, f"Pagina {doc.page}")
    canvas.restoreState()


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = stylesheet()
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Smart Dispatch IA - Informe Final",
        author="Smart Dispatch IA",
    )
    doc.build(build_story(styles), onFirstPage=footer, onLaterPages=footer)
    DOCS_OUTPUT.write_bytes(OUTPUT.read_bytes())
    print(f"Wrote {OUTPUT}")
    print(f"Wrote {DOCS_OUTPUT}")


if __name__ == "__main__":
    main()
