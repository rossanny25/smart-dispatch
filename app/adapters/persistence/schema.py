from sqlalchemy import (
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
)


metadata = MetaData()

work_orders = Table(
    "work_orders",
    metadata,
    Column("id", Text, primary_key=True, nullable=False),
    Column("schema_version", Text, nullable=False),
    Column("raw_input_json", Text, nullable=False),
    Column("incident_text", Text, nullable=False),
    Column("address", Text, nullable=False),
    Column("zone", Text, nullable=False),
    Column("context_json", Text, nullable=False),
    Column("created_at", Text, nullable=False),
)

idempotency_records = Table(
    "idempotency_records",
    metadata,
    Column("route", Text, nullable=False),
    Column("idempotency_key", Text, nullable=False),
    Column("request_hash", Text, nullable=False),
    Column("response_status", Integer, nullable=False),
    Column("response_body_json", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    PrimaryKeyConstraint("route", "idempotency_key"),
)

configuration_versions = Table(
    "configuration_versions",
    metadata,
    Column("version", Text, primary_key=True, nullable=False),
    Column("contract_version", Text, nullable=False),
    Column("registry_json", Text, nullable=False),
    Column("registry_sha256", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    CheckConstraint(
        "contract_version = 'v1'",
        name="ck_configuration_contract_version",
    ),
    CheckConstraint(
        "json_valid(registry_json)",
        name="ck_configuration_registry_json",
    ),
    CheckConstraint(
        "length(registry_sha256) = 64 "
        "AND registry_sha256 NOT GLOB '*[^0-9a-f]*'",
        name="ck_configuration_registry_sha256",
    ),
)

app_users = Table(
    "app_users",
    metadata,
    Column("id", Text, primary_key=True, nullable=False),
    Column("username", Text, nullable=False),
    Column("display_name", Text, nullable=False),
    Column("role", Text, nullable=False),
    Column("password_hash", Text, nullable=False),
    Column("is_active", Integer, nullable=False),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
    UniqueConstraint("username", name="uq_app_users_username"),
    CheckConstraint(
        "role IN ('admin','tecnico','dispatcher')",
        name="ck_app_users_role",
    ),
    CheckConstraint("is_active IN (0, 1)", name="ck_app_users_active"),
    CheckConstraint("length(username) BETWEEN 3 AND 80", name="ck_app_users_username"),
    CheckConstraint("length(display_name) BETWEEN 1 AND 120", name="ck_app_users_name"),
    CheckConstraint(
        "password_hash LIKE 'pbkdf2_sha256$%'",
        name="ck_app_users_password_hash",
    ),
)

service_technicians = Table(
    "service_technicians",
    metadata,
    Column("id", Text, primary_key=True, nullable=False),
    Column("name", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("zone", Text, nullable=False),
    Column("certifications_json", Text, nullable=False),
    Column("shift_start", Text, nullable=False),
    Column("shift_end", Text, nullable=False),
    Column("active_workload_hours", Float, nullable=False),
    Column("rating", Float, nullable=False),
    Column("ppe_json", Text, nullable=False),
    Column("gps_json", Text, nullable=False),
    Column("contact_phone", Text, nullable=False),
    Column("contact_email", Text, nullable=False),
    Column("documents_json", Text, nullable=False),
    Column("audit_log_json", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
    UniqueConstraint("name", name="uq_service_technicians_name"),
    CheckConstraint(
        "status IN ('disponible','ocupado','fuera_servicio')",
        name="ck_service_technicians_status",
    ),
    CheckConstraint("length(name) BETWEEN 2 AND 120", name="ck_service_technicians_name"),
    CheckConstraint("length(zone) BETWEEN 2 AND 80", name="ck_service_technicians_zone"),
    CheckConstraint("active_workload_hours BETWEEN 0 AND 16", name="ck_service_technicians_workload"),
    CheckConstraint("rating BETWEEN 0 AND 5", name="ck_service_technicians_rating"),
    CheckConstraint(
        "shift_start GLOB '[0-2][0-9]:[0-5][0-9]' AND substr(shift_start, 1, 2) < '24'",
        name="ck_service_technicians_shift_start",
    ),
    CheckConstraint(
        "shift_end GLOB '[0-2][0-9]:[0-5][0-9]' AND substr(shift_end, 1, 2) < '24'",
        name="ck_service_technicians_shift_end",
    ),
    CheckConstraint(
        "json_valid(certifications_json) AND json_type(certifications_json) = 'array'",
        name="ck_service_technicians_certifications",
    ),
    CheckConstraint(
        "json_valid(ppe_json) AND json_type(ppe_json) = 'array'",
        name="ck_service_technicians_ppe",
    ),
    CheckConstraint("json_valid(gps_json)", name="ck_service_technicians_gps"),
    CheckConstraint(
        "json_type(gps_json) = 'object' "
        "AND json_type(gps_json, '$.lat') IN ('integer','real') "
        "AND json_type(gps_json, '$.lng') IN ('integer','real')",
        name="ck_service_technicians_gps_shape",
    ),
    CheckConstraint("json_valid(documents_json)", name="ck_service_technicians_documents"),
    CheckConstraint("json_valid(audit_log_json)", name="ck_service_technicians_audit"),
)

service_orders = Table(
    "service_orders",
    metadata,
    Column("id", Text, primary_key=True, nullable=False),
    Column("client", Text, nullable=False),
    Column("address", Text, nullable=False),
    Column("zone", Text, nullable=False),
    Column("raw_text", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("structured_data_json", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
    CheckConstraint(
        "status IN ('pendiente','completada','cancelada')",
        name="ck_service_orders_status",
    ),
    CheckConstraint("length(id) BETWEEN 1 AND 120", name="ck_service_orders_id"),
    CheckConstraint("length(client) BETWEEN 1 AND 160", name="ck_service_orders_client"),
    CheckConstraint("length(zone) BETWEEN 2 AND 80", name="ck_service_orders_zone"),
    CheckConstraint("json_valid(structured_data_json)", name="ck_service_orders_structured"),
)

Index("ix_service_orders_status_zone", service_orders.c.status, service_orders.c.zone)

service_visits = Table(
    "service_visits",
    metadata,
    Column("id", Text, primary_key=True, nullable=False),
    Column("order_id", Text, nullable=False),
    Column(
        "technician_id",
        Text,
        ForeignKey("service_technicians.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("technician_name", Text, nullable=False),
    Column("client", Text, nullable=False),
    Column("address", Text, nullable=False),
    Column("zone", Text, nullable=False),
    Column("category", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("scheduled_start_at", Text, nullable=False),
    Column("scheduled_end_at", Text, nullable=False),
    Column("duration_minutes", Integer, nullable=False),
    Column("feedback_comment", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
    CheckConstraint(
        "status IN ('programada','en_curso','completada','cancelada')",
        name="ck_service_visits_status",
    ),
    CheckConstraint("duration_minutes BETWEEN 1 AND 1440", name="ck_service_visits_duration"),
    CheckConstraint("length(order_id) BETWEEN 1 AND 120", name="ck_service_visits_order"),
    CheckConstraint("length(technician_name) BETWEEN 2 AND 120", name="ck_service_visits_technician_name"),
    CheckConstraint("length(zone) BETWEEN 2 AND 80", name="ck_service_visits_zone"),
    UniqueConstraint("order_id", name="uq_service_visits_order"),
)

Index("ix_service_visits_technician_start", service_visits.c.technician_id, service_visits.c.scheduled_start_at)
Index("ix_service_visits_start", service_visits.c.scheduled_start_at)

work_order_analyses = Table(
    "work_order_analyses",
    metadata,
    Column("id", Text, primary_key=True, nullable=False),
    Column(
        "work_order_id",
        Text,
        ForeignKey("work_orders.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("schema_version", Text, nullable=False),
    Column(
        "configuration_version",
        Text,
        ForeignKey("configuration_versions.version", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("input_hash", Text, nullable=False),
    Column("output_json", Text, nullable=False),
    Column("category", Text, nullable=False),
    Column("priority", Integer, nullable=False),
    Column("sla_target_minutes", Integer, nullable=False),
    Column("required_certifications_json", Text, nullable=False),
    Column("estimated_service_duration_minutes", Integer, nullable=False),
    Column("created_at", Text, nullable=False),
    CheckConstraint("priority BETWEEN 1 AND 5", name="ck_analysis_priority"),
    CheckConstraint("schema_version = 'v1'", name="ck_analysis_schema_version"),
    CheckConstraint(
        "configuration_version = 'analysis-v1'",
        name="ck_analysis_configuration_version",
    ),
    CheckConstraint(
        "category IN ('gas','electricity','telecommunications',"
        "'plumbing','hvac','maintenance')",
        name="ck_analysis_category",
    ),
    CheckConstraint(
        "length(input_hash) = 64 AND input_hash NOT GLOB '*[^0-9a-f]*'",
        name="ck_analysis_input_hash",
    ),
    CheckConstraint("json_valid(output_json)", name="ck_analysis_output_json"),
    CheckConstraint(
        "json_valid(required_certifications_json)",
        name="ck_analysis_certifications_json",
    ),
    CheckConstraint(
        "sla_target_minutes BETWEEN 1 AND 10080",
        name="ck_analysis_sla_minutes",
    ),
    CheckConstraint(
        "estimated_service_duration_minutes BETWEEN 15 AND 1440",
        name="ck_analysis_duration_minutes",
    ),
    UniqueConstraint(
        "work_order_id",
        "configuration_version",
        name="uq_work_order_analysis_configuration",
    ),
)
Index(
    "uq_analysis_id_work_order",
    work_order_analyses.c.id,
    work_order_analyses.c.work_order_id,
    unique=True,
)

eligibility_evaluation_sets = Table(
    "eligibility_evaluation_sets",
    metadata,
    Column("id", Text, primary_key=True, nullable=False),
    Column(
        "work_order_id",
        Text,
        ForeignKey("work_orders.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "work_order_analysis_id",
        Text,
        nullable=False,
    ),
    Column("schema_version", Text, nullable=False),
    Column(
        "configuration_version",
        Text,
        ForeignKey("configuration_versions.version", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("input_hash", Text, nullable=False),
    Column("input_json", Text, nullable=False),
    Column("output_json", Text, nullable=False),
    Column("candidate_count", Integer, nullable=False),
    Column("eligible_count", Integer, nullable=False),
    Column("ineligible_count", Integer, nullable=False),
    Column("no_feasible_candidates", Integer, nullable=False),
    Column("created_at", Text, nullable=False),
    CheckConstraint(
        "schema_version = 'v1'",
        name="ck_eligibility_schema_version",
    ),
    CheckConstraint(
        "configuration_version = 'eligibility-v1'",
        name="ck_eligibility_configuration_version",
    ),
    CheckConstraint(
        "length(input_hash) = 64 AND input_hash NOT GLOB '*[^0-9a-f]*'",
        name="ck_eligibility_input_hash",
    ),
    CheckConstraint("json_valid(input_json)", name="ck_eligibility_input_json"),
    CheckConstraint("json_valid(output_json)", name="ck_eligibility_output_json"),
    CheckConstraint(
        "candidate_count BETWEEN 0 AND 100",
        name="ck_eligibility_candidate_count",
    ),
    CheckConstraint(
        "eligible_count BETWEEN 0 AND candidate_count",
        name="ck_eligibility_eligible_count",
    ),
    CheckConstraint(
        "ineligible_count BETWEEN 0 AND candidate_count",
        name="ck_eligibility_ineligible_count",
    ),
    CheckConstraint(
        "eligible_count + ineligible_count = candidate_count",
        name="ck_eligibility_partition_count",
    ),
    CheckConstraint(
        "no_feasible_candidates IN (0, 1)",
        name="ck_eligibility_no_feasible_boolean",
    ),
    CheckConstraint(
        "(no_feasible_candidates = 1 AND eligible_count = 0) "
        "OR (no_feasible_candidates = 0 AND eligible_count > 0)",
        name="ck_eligibility_no_feasible_consistency",
    ),
    ForeignKeyConstraint(
        ["work_order_analysis_id", "work_order_id"],
        ["work_order_analyses.id", "work_order_analyses.work_order_id"],
        ondelete="RESTRICT",
        name="fk_eligibility_analysis_work_order",
    ),
    UniqueConstraint(
        "work_order_analysis_id",
        "configuration_version",
        "input_hash",
        name="uq_eligibility_analysis_configuration_input",
    ),
)

scoring_evaluation_sets = Table(
    "scoring_evaluation_sets",
    metadata,
    Column("id", Text, primary_key=True, nullable=False),
    Column(
        "eligibility_evaluation_set_id",
        Text,
        ForeignKey("eligibility_evaluation_sets.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("schema_version", Text, nullable=False),
    Column(
        "configuration_version",
        Text,
        ForeignKey("configuration_versions.version", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("input_hash", Text, nullable=False),
    Column("input_json", Text, nullable=False),
    Column("output_json", Text, nullable=False),
    Column("candidate_count", Integer, nullable=False),
    Column("eligible_count", Integer, nullable=False),
    Column("ineligible_count", Integer, nullable=False),
    Column("top_technician_id", Text, nullable=True),
    Column("top_objective_score", Text, nullable=True),
    Column("created_at", Text, nullable=False),
    CheckConstraint(
        "schema_version = 'v1'",
        name="ck_scoring_schema_version",
    ),
    CheckConstraint(
        "configuration_version = 'scoring-v1'",
        name="ck_scoring_configuration_version",
    ),
    CheckConstraint(
        "length(input_hash) = 64 AND input_hash NOT GLOB '*[^0-9a-f]*'",
        name="ck_scoring_input_hash",
    ),
    CheckConstraint("json_valid(input_json)", name="ck_scoring_input_json"),
    CheckConstraint("json_valid(output_json)", name="ck_scoring_output_json"),
    CheckConstraint(
        "candidate_count BETWEEN 0 AND 100",
        name="ck_scoring_candidate_count",
    ),
    CheckConstraint(
        "eligible_count BETWEEN 0 AND candidate_count",
        name="ck_scoring_eligible_count",
    ),
    CheckConstraint(
        "ineligible_count BETWEEN 0 AND candidate_count",
        name="ck_scoring_ineligible_count",
    ),
    CheckConstraint(
        "eligible_count + ineligible_count = candidate_count",
        name="ck_scoring_partition_count",
    ),
    CheckConstraint(
        "(eligible_count = 0 AND top_technician_id IS NULL "
        "AND top_objective_score IS NULL) OR "
        "(eligible_count > 0 AND top_technician_id IS NOT NULL "
        "AND top_objective_score IS NOT NULL)",
        name="ck_scoring_top_consistency",
    ),
    CheckConstraint(
        "top_objective_score IS NULL OR "
        "(length(top_objective_score) BETWEEN 1 AND 80 "
        "AND top_objective_score NOT GLOB '*[^0-9.-]*')",
        name="ck_scoring_top_score_shape",
    ),
    UniqueConstraint(
        "eligibility_evaluation_set_id",
        "configuration_version",
        "input_hash",
        name="uq_scoring_eligibility_configuration_input",
    ),
)

confidence_evaluation_sets = Table(
    "confidence_evaluation_sets",
    metadata,
    Column("id", Text, primary_key=True, nullable=False),
    Column(
        "scoring_evaluation_set_id",
        Text,
        ForeignKey("scoring_evaluation_sets.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("schema_version", Text, nullable=False),
    Column(
        "configuration_version",
        Text,
        ForeignKey("configuration_versions.version", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("input_hash", Text, nullable=False),
    Column("input_json", Text, nullable=False),
    Column("output_json", Text, nullable=False),
    Column("eligible_count", Integer, nullable=False),
    Column("source_count", Integer, nullable=False),
    Column("warning_count", Integer, nullable=False),
    Column("recommended_technician_id", Text, nullable=True),
    Column("confidence_value", Text, nullable=True),
    Column("confidence_label", Text, nullable=True),
    Column("created_at", Text, nullable=False),
    CheckConstraint(
        "schema_version = 'v1'", name="ck_confidence_schema_version"
    ),
    CheckConstraint(
        "configuration_version = 'confidence-v1'",
        name="ck_confidence_configuration_version",
    ),
    CheckConstraint(
        "length(input_hash) = 64 AND input_hash NOT GLOB '*[^0-9a-f]*'",
        name="ck_confidence_input_hash",
    ),
    CheckConstraint("json_valid(input_json)", name="ck_confidence_input_json"),
    CheckConstraint("json_valid(output_json)", name="ck_confidence_output_json"),
    CheckConstraint(
        "eligible_count BETWEEN 0 AND 100",
        name="ck_confidence_eligible_count",
    ),
    CheckConstraint(
        "source_count BETWEEN 0 AND 103",
        name="ck_confidence_source_count",
    ),
    CheckConstraint(
        "warning_count BETWEEN 0 AND source_count",
        name="ck_confidence_warning_count",
    ),
    CheckConstraint(
        "(eligible_count = 0 AND recommended_technician_id IS NULL "
        "AND confidence_value IS NULL AND confidence_label IS NULL) OR "
        "(eligible_count > 0 AND recommended_technician_id IS NOT NULL "
        "AND confidence_value IS NOT NULL "
        "AND confidence_label IN ('low','medium','high'))",
        name="ck_confidence_summary_consistency",
    ),
    UniqueConstraint(
        "scoring_evaluation_set_id",
        "configuration_version",
        "input_hash",
        name="uq_confidence_scoring_configuration_input",
    ),
)

dispatch_runs = Table(
    "dispatch_runs",
    metadata,
    Column("id", Text, primary_key=True, nullable=False),
    Column(
        "work_order_id",
        Text,
        ForeignKey("work_orders.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("schema_version", Text, nullable=False),
    Column(
        "configuration_version",
        Text,
        ForeignKey("configuration_versions.version", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("state", Text, nullable=False),
    Column("revision", Integer, nullable=False),
    Column("snapshot_json", Text, nullable=False),
    Column("snapshot_sha256", Text, nullable=False),
    Column("resource_json", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
    CheckConstraint("schema_version = 'v1'", name="ck_dispatch_schema_version"),
    CheckConstraint(
        "configuration_version = 'dispatch-v1'",
        name="ck_dispatch_configuration_version",
    ),
    CheckConstraint(
        "state IN ('CAPTURE','ANALYZE','PLAN','EVALUATE',"
        "'WAIT_FOR_DECISION','NO_FEASIBLE_CANDIDATES','FAILED')",
        name="ck_dispatch_state",
    ),
    CheckConstraint("revision BETWEEN 0 AND 4", name="ck_dispatch_revision"),
    CheckConstraint("json_valid(snapshot_json)", name="ck_dispatch_snapshot_json"),
    CheckConstraint("json_valid(resource_json)", name="ck_dispatch_resource_json"),
    CheckConstraint(
        "length(snapshot_sha256) = 64 "
        "AND snapshot_sha256 NOT GLOB '*[^0-9a-f]*'",
        name="ck_dispatch_snapshot_sha256",
    ),
)

run_snapshots = Table(
    "run_snapshots",
    metadata,
    Column("id", Text, primary_key=True, nullable=False),
    Column(
        "run_id",
        Text,
        ForeignKey("dispatch_runs.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("kind", Text, nullable=False),
    Column("stage", Text, nullable=True),
    Column("content_json", Text, nullable=False),
    Column("content_sha256", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    CheckConstraint(
        "kind IN ('run_input','stage_output')", name="ck_run_snapshot_kind"
    ),
    CheckConstraint("json_valid(content_json)", name="ck_run_snapshot_json"),
    CheckConstraint(
        "length(content_sha256) = 64 "
        "AND content_sha256 NOT GLOB '*[^0-9a-f]*'",
        name="ck_run_snapshot_sha256",
    ),
    UniqueConstraint("id", "run_id", name="uq_run_snapshot_id_run"),
    UniqueConstraint("run_id", "kind", "stage", name="uq_run_snapshot_kind_stage"),
)
Index(
    "uq_run_input_snapshot",
    run_snapshots.c.run_id,
    unique=True,
    sqlite_where=run_snapshots.c.kind == "run_input",
)

stage_executions = Table(
    "stage_executions",
    metadata,
    Column("id", Text, primary_key=True, nullable=False),
    Column(
        "run_id",
        Text,
        ForeignKey("dispatch_runs.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("sequence", Integer, nullable=False),
    Column("schema_version", Text, nullable=False),
    Column("configuration_version", Text, nullable=False),
    Column("stage", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("started_at", Text, nullable=False),
    Column("ended_at", Text, nullable=False),
    Column("duration_ms", Integer, nullable=False),
    Column("attempt", Integer, nullable=False),
    Column("input_ref", Text, nullable=False),
    Column("run_snapshot_ref", Text, nullable=False),
    Column("output_ref", Text, nullable=True),
    Column("error_code", Text, nullable=True),
    Column("error_type", Text, nullable=True),
    Column("safe_message", Text, nullable=True),
    CheckConstraint("sequence BETWEEN 1 AND 4", name="ck_stage_sequence"),
    CheckConstraint(
        "(sequence = 1 AND stage = 'CAPTURE') OR "
        "(sequence = 2 AND stage = 'ANALYZE') OR "
        "(sequence = 3 AND stage = 'PLAN') OR "
        "(sequence = 4 AND stage = 'EVALUATE')",
        name="ck_stage_sequence_name",
    ),
    CheckConstraint("schema_version = 'v1'", name="ck_stage_schema_version"),
    CheckConstraint(
        "configuration_version = 'dispatch-v1'",
        name="ck_stage_configuration_version",
    ),
    CheckConstraint("duration_ms >= 0", name="ck_stage_duration"),
    CheckConstraint("ended_at >= started_at", name="ck_stage_timing"),
    CheckConstraint("attempt = 1", name="ck_stage_attempt"),
    CheckConstraint("status IN ('completed','failed')", name="ck_stage_status"),
    CheckConstraint(
        "(status = 'completed' AND output_ref IS NOT NULL "
        "AND error_code IS NULL AND error_type IS NULL AND safe_message IS NULL) "
        "OR (status = 'failed' AND output_ref IS NULL "
        "AND error_code IS NOT NULL AND error_type = 'STAGE_FAILURE' "
        "AND safe_message IS NOT NULL)",
        name="ck_stage_result_consistency",
    ),
    ForeignKeyConstraint(
        ["input_ref", "run_id"],
        ["run_snapshots.id", "run_snapshots.run_id"],
        ondelete="RESTRICT",
        name="fk_stage_input_snapshot_run",
    ),
    ForeignKeyConstraint(
        ["run_snapshot_ref", "run_id"],
        ["run_snapshots.id", "run_snapshots.run_id"],
        ondelete="RESTRICT",
        name="fk_stage_run_snapshot_run",
    ),
    ForeignKeyConstraint(
        ["output_ref", "run_id"],
        ["run_snapshots.id", "run_snapshots.run_id"],
        ondelete="RESTRICT",
        name="fk_stage_output_snapshot_run",
    ),
    UniqueConstraint("run_id", "sequence", name="uq_stage_run_sequence"),
)

state_transitions = Table(
    "state_transitions",
    metadata,
    Column("id", Text, primary_key=True, nullable=False),
    Column(
        "run_id",
        Text,
        ForeignKey("dispatch_runs.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("sequence", Integer, nullable=False),
    Column("from_state", Text, nullable=True),
    Column("to_state", Text, nullable=False),
    Column("outcome_code", Text, nullable=False),
    Column("run_revision", Integer, nullable=False),
    Column("configuration_version", Text, nullable=False),
    Column("occurred_at", Text, nullable=False),
    CheckConstraint("sequence BETWEEN 0 AND 4", name="ck_transition_sequence"),
    CheckConstraint(
        "run_revision = sequence", name="ck_transition_revision"
    ),
    CheckConstraint(
        "configuration_version = 'dispatch-v1'",
        name="ck_transition_configuration_version",
    ),
    CheckConstraint(
        "(from_state IS NULL AND to_state = 'CAPTURE') OR "
        "(from_state = 'CAPTURE' AND to_state IN ('ANALYZE','FAILED')) OR "
        "(from_state = 'ANALYZE' AND to_state IN ('PLAN','FAILED')) OR "
        "(from_state = 'PLAN' AND to_state IN ('EVALUATE','FAILED')) OR "
        "(from_state = 'EVALUATE' AND to_state IN "
        "('WAIT_FOR_DECISION','NO_FEASIBLE_CANDIDATES','FAILED'))",
        name="ck_transition_legal",
    ),
    UniqueConstraint("run_id", "sequence", name="uq_transition_run_sequence"),
)
