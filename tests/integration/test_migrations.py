from pathlib import Path

from alembic import command
import pytest
from sqlalchemy import text


def test_fresh_database_migrates_to_head_with_minimal_schema(tmp_path: Path) -> None:
    from app.migrations.runtime import (
        get_current_revision,
        get_head_revision,
        upgrade_to_head,
    )
    from app.adapters.persistence.database import create_sqlite_engine

    database_path = tmp_path / "fresh.db"

    assert get_current_revision(database_path) is None
    upgrade_to_head(database_path)

    assert get_current_revision(database_path) == get_head_revision()
    engine = create_sqlite_engine(database_path)
    try:
        with engine.connect() as connection:
            objects = set(
                connection.execute(
                    text(
                        "SELECT type, name FROM sqlite_schema "
                        "WHERE name NOT LIKE 'sqlite_%'"
                    )
                ).all()
            )
        assert objects == {
            ("table", "alembic_version"),
            ("table", "work_orders"),
            ("table", "idempotency_records"),
            ("table", "configuration_versions"),
            ("table", "work_order_analyses"),
            ("table", "eligibility_evaluation_sets"),
            ("table", "scoring_evaluation_sets"),
                ("table", "confidence_evaluation_sets"),
                ("table", "dispatch_runs"),
                ("table", "run_snapshots"),
                ("table", "stage_executions"),
                ("table", "state_transitions"),
                ("index", "uq_analysis_id_work_order"),
                ("index", "uq_run_input_snapshot"),
        }
    finally:
        engine.dispose()


def test_pending_migration_detection_is_stable_outside_project_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from app.migrations.runtime import has_pending_migrations, upgrade_to_head

    database_path = tmp_path / "pending.db"
    monkeypatch.chdir(tmp_path)

    assert has_pending_migrations(database_path)
    upgrade_to_head(database_path)
    assert not has_pending_migrations(database_path)


def test_existing_story_1_1_database_upgrades_incrementally_to_head(
    tmp_path: Path,
) -> None:
    from app.adapters.persistence.database import create_sqlite_engine
    from app.migrations.runtime import (
        build_alembic_config,
        get_current_revision,
        get_head_revision,
        upgrade_to_head,
    )

    database_path = tmp_path / "story-1-1.db"
    engine = create_sqlite_engine(database_path)
    config = build_alembic_config(database_path)
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "20260727_0001")
    finally:
        engine.dispose()
    assert get_current_revision(database_path) == "20260727_0001"

    upgrade_to_head(database_path)

    assert get_current_revision(database_path) == get_head_revision()
    engine = create_sqlite_engine(database_path)
    try:
        with engine.connect() as connection:
            tables = set(
                connection.execute(
                    text(
                        "SELECT name FROM sqlite_schema "
                        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                    )
                ).scalars()
            )
        assert tables == {
            "alembic_version",
            "work_orders",
            "idempotency_records",
            "configuration_versions",
            "work_order_analyses",
            "eligibility_evaluation_sets",
            "scoring_evaluation_sets",
            "confidence_evaluation_sets",
            "dispatch_runs",
            "run_snapshots",
            "stage_executions",
            "state_transitions",
        }
    finally:
        engine.dispose()


def test_existing_story_1_2_database_upgrades_incrementally_to_head(
    tmp_path: Path,
) -> None:
    from app.adapters.persistence.database import create_sqlite_engine
    from app.migrations.runtime import (
        build_alembic_config,
        get_current_revision,
        get_head_revision,
        upgrade_to_head,
    )

    database_path = tmp_path / "story-1-2.db"
    engine = create_sqlite_engine(database_path)
    config = build_alembic_config(database_path)
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "20260728_0002")
    finally:
        engine.dispose()
    assert get_current_revision(database_path) == "20260728_0002"

    upgrade_to_head(database_path)

    assert get_current_revision(database_path) == get_head_revision()
    engine = create_sqlite_engine(database_path)
    try:
        with engine.connect() as connection:
            tables = set(
                connection.execute(
                    text(
                        "SELECT name FROM sqlite_schema "
                        "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                    )
                ).scalars()
            )
        assert tables == {
            "alembic_version",
            "work_orders",
            "idempotency_records",
            "configuration_versions",
            "work_order_analyses",
            "eligibility_evaluation_sets",
            "scoring_evaluation_sets",
            "confidence_evaluation_sets",
            "dispatch_runs",
            "run_snapshots",
            "stage_executions",
            "state_transitions",
        }
    finally:
        engine.dispose()


def test_existing_story_1_3_database_upgrades_incrementally_to_head(
    tmp_path: Path,
) -> None:
    from app.adapters.persistence.database import create_sqlite_engine
    from app.migrations.runtime import (
        build_alembic_config,
        get_current_revision,
        get_head_revision,
        upgrade_to_head,
    )

    database_path = tmp_path / "story-1-3.db"
    engine = create_sqlite_engine(database_path)
    config = build_alembic_config(database_path)
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "20260728_0003")
    finally:
        engine.dispose()
    assert get_current_revision(database_path) == "20260728_0003"

    upgrade_to_head(database_path)

    assert get_current_revision(database_path) == get_head_revision()
    engine = create_sqlite_engine(database_path)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT count(*) FROM sqlite_schema "
                    "WHERE type = 'table' "
                    "AND name = 'eligibility_evaluation_sets'"
                )
            ).scalar_one() == 1
    finally:
        engine.dispose()


def test_existing_story_1_4_database_upgrades_incrementally_to_head(
    tmp_path: Path,
) -> None:
    from app.adapters.persistence.database import create_sqlite_engine
    from app.migrations.runtime import (
        build_alembic_config,
        get_current_revision,
        get_head_revision,
        upgrade_to_head,
    )

    database_path = tmp_path / "story-1-4.db"
    engine = create_sqlite_engine(database_path)
    config = build_alembic_config(database_path)
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "20260728_0004")
    finally:
        engine.dispose()
    assert get_current_revision(database_path) == "20260728_0004"

    upgrade_to_head(database_path)

    assert get_current_revision(database_path) == get_head_revision()
    engine = create_sqlite_engine(database_path)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT count(*) FROM sqlite_schema "
                    "WHERE type = 'table' "
                    "AND name = 'scoring_evaluation_sets'"
                )
            ).scalar_one() == 1
    finally:
        engine.dispose()


def test_existing_story_1_5_database_upgrades_to_confidence_head(
    tmp_path: Path,
) -> None:
    from app.adapters.persistence.database import create_sqlite_engine
    from app.migrations.runtime import (
        build_alembic_config,
        get_current_revision,
        get_head_revision,
        upgrade_to_head,
    )

    database_path = tmp_path / "story-1-5.db"
    engine = create_sqlite_engine(database_path)
    config = build_alembic_config(database_path)
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "20260728_0005")
    finally:
        engine.dispose()
    assert get_current_revision(database_path) == "20260728_0005"

    upgrade_to_head(database_path)

    assert get_current_revision(database_path) == get_head_revision()
    engine = create_sqlite_engine(database_path)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT count(*) FROM sqlite_schema "
                    "WHERE type = 'table' "
                    "AND name = 'confidence_evaluation_sets'"
                )
            ).scalar_one() == 1
    finally:
        engine.dispose()


def test_confidence_schema_has_expected_columns_and_foreign_keys(
    tmp_path: Path,
) -> None:
    from app.adapters.persistence.database import create_sqlite_engine
    from app.migrations.runtime import upgrade_to_head

    path = tmp_path / "confidence-schema.db"
    upgrade_to_head(path)
    engine = create_sqlite_engine(path)
    try:
        with engine.connect() as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    text("PRAGMA table_info(confidence_evaluation_sets)")
                )
            }
            foreign_tables = {
                row[2]
                for row in connection.execute(
                    text("PRAGMA foreign_key_list(confidence_evaluation_sets)")
                )
            }
            sql = connection.execute(
                text(
                    "SELECT sql FROM sqlite_schema "
                    "WHERE type='table' AND name='confidence_evaluation_sets'"
                )
            ).scalar_one()
        assert columns == {
            "id",
            "scoring_evaluation_set_id",
            "schema_version",
            "configuration_version",
            "input_hash",
            "input_json",
            "output_json",
            "eligible_count",
            "source_count",
            "warning_count",
            "recommended_technician_id",
            "confidence_value",
            "confidence_label",
            "created_at",
        }
        assert foreign_tables == {
            "scoring_evaluation_sets",
            "configuration_versions",
        }
        assert "uq_confidence_scoring_configuration_input" in sql
        assert "ck_confidence_summary_consistency" in sql
    finally:
        engine.dispose()


def test_migrations_target_exact_filename_with_url_metacharacters(
    tmp_path: Path,
) -> None:
    from app.migrations.runtime import get_current_revision, get_head_revision, upgrade_to_head

    database_path = tmp_path / "runtime?#%.db"

    upgrade_to_head(database_path)

    assert database_path.exists()
    assert get_current_revision(database_path) == get_head_revision()
    assert not (tmp_path / "runtime").exists()


def test_work_order_schema_has_exact_columns_and_constraints(tmp_path: Path) -> None:
    from app.migrations.runtime import upgrade_to_head
    from app.adapters.persistence.database import create_sqlite_engine

    database_path = tmp_path / "schema.db"
    upgrade_to_head(database_path)
    engine = create_sqlite_engine(database_path)
    try:
        with engine.connect() as connection:
            work_order_columns = connection.execute(
                text("PRAGMA table_info(work_orders)")
            ).all()
            idempotency_columns = connection.execute(
                text("PRAGMA table_info(idempotency_records)")
            ).all()
            configuration_columns = connection.execute(
                text("PRAGMA table_info(configuration_versions)")
            ).all()
            analysis_columns = connection.execute(
                text("PRAGMA table_info(work_order_analyses)")
            ).all()
            eligibility_columns = connection.execute(
                text("PRAGMA table_info(eligibility_evaluation_sets)")
            ).all()
            scoring_columns = connection.execute(
                text("PRAGMA table_info(scoring_evaluation_sets)")
            ).all()
            eligibility_sql = connection.execute(
                text(
                    "SELECT sql FROM sqlite_schema "
                    "WHERE type = 'table' "
                    "AND name = 'eligibility_evaluation_sets'"
                )
            ).scalar_one()
            analysis_indexes = connection.execute(
                text("PRAGMA index_list(work_order_analyses)")
            ).all()
            eligibility_foreign_keys = connection.execute(
                text("PRAGMA foreign_key_list(eligibility_evaluation_sets)")
            ).all()
            scoring_sql = connection.execute(
                text(
                    "SELECT sql FROM sqlite_schema "
                    "WHERE type = 'table' "
                    "AND name = 'scoring_evaluation_sets'"
                )
            ).scalar_one()
            scoring_foreign_keys = connection.execute(
                text("PRAGMA foreign_key_list(scoring_evaluation_sets)")
            ).all()
        assert [(row.name, row.type, row.notnull, row.pk) for row in work_order_columns] == [
            ("id", "TEXT", 1, 1),
            ("schema_version", "TEXT", 1, 0),
            ("raw_input_json", "TEXT", 1, 0),
            ("incident_text", "TEXT", 1, 0),
            ("address", "TEXT", 1, 0),
            ("zone", "TEXT", 1, 0),
            ("context_json", "TEXT", 1, 0),
            ("created_at", "TEXT", 1, 0),
        ]
        assert [
            (row.name, row.type, row.notnull, row.pk)
            for row in idempotency_columns
        ] == [
            ("route", "TEXT", 1, 1),
            ("idempotency_key", "TEXT", 1, 2),
            ("request_hash", "TEXT", 1, 0),
            ("response_status", "INTEGER", 1, 0),
            ("response_body_json", "TEXT", 1, 0),
            ("created_at", "TEXT", 1, 0),
        ]
        assert [
            (row.name, row.type, row.notnull, row.pk)
            for row in configuration_columns
        ] == [
            ("version", "TEXT", 1, 1),
            ("contract_version", "TEXT", 1, 0),
            ("registry_json", "TEXT", 1, 0),
            ("registry_sha256", "TEXT", 1, 0),
            ("created_at", "TEXT", 1, 0),
        ]
        assert [(row.name, row.type, row.notnull, row.pk) for row in analysis_columns] == [
            ("id", "TEXT", 1, 1),
            ("work_order_id", "TEXT", 1, 0),
            ("schema_version", "TEXT", 1, 0),
            ("configuration_version", "TEXT", 1, 0),
            ("input_hash", "TEXT", 1, 0),
            ("output_json", "TEXT", 1, 0),
            ("category", "TEXT", 1, 0),
            ("priority", "INTEGER", 1, 0),
            ("sla_target_minutes", "INTEGER", 1, 0),
            ("required_certifications_json", "TEXT", 1, 0),
            ("estimated_service_duration_minutes", "INTEGER", 1, 0),
            ("created_at", "TEXT", 1, 0),
        ]
        assert [
            (row.name, row.type, row.notnull, row.pk)
            for row in eligibility_columns
        ] == [
            ("id", "TEXT", 1, 1),
            ("work_order_id", "TEXT", 1, 0),
            ("work_order_analysis_id", "TEXT", 1, 0),
            ("schema_version", "TEXT", 1, 0),
            ("configuration_version", "TEXT", 1, 0),
            ("input_hash", "TEXT", 1, 0),
            ("input_json", "TEXT", 1, 0),
            ("output_json", "TEXT", 1, 0),
            ("candidate_count", "INTEGER", 1, 0),
            ("eligible_count", "INTEGER", 1, 0),
            ("ineligible_count", "INTEGER", 1, 0),
            ("no_feasible_candidates", "INTEGER", 1, 0),
            ("created_at", "TEXT", 1, 0),
        ]
        assert [
            (row.name, row.type, row.notnull, row.pk)
            for row in scoring_columns
        ] == [
            ("id", "TEXT", 1, 1),
            ("eligibility_evaluation_set_id", "TEXT", 1, 0),
            ("schema_version", "TEXT", 1, 0),
            ("configuration_version", "TEXT", 1, 0),
            ("input_hash", "TEXT", 1, 0),
            ("input_json", "TEXT", 1, 0),
            ("output_json", "TEXT", 1, 0),
            ("candidate_count", "INTEGER", 1, 0),
            ("eligible_count", "INTEGER", 1, 0),
            ("ineligible_count", "INTEGER", 1, 0),
            ("top_technician_id", "TEXT", 0, 0),
            ("top_objective_score", "TEXT", 0, 0),
            ("created_at", "TEXT", 1, 0),
        ]
        for constraint in (
            "ck_eligibility_schema_version",
            "ck_eligibility_configuration_version",
            "ck_eligibility_input_hash",
            "ck_eligibility_input_json",
            "ck_eligibility_output_json",
            "ck_eligibility_candidate_count",
            "ck_eligibility_eligible_count",
            "ck_eligibility_ineligible_count",
            "ck_eligibility_partition_count",
            "ck_eligibility_no_feasible_boolean",
            "ck_eligibility_no_feasible_consistency",
            "uq_eligibility_analysis_configuration_input",
            "fk_eligibility_analysis_work_order",
        ):
            assert constraint in eligibility_sql
        assert any(
            row.name == "uq_analysis_id_work_order" and row.unique == 1
            for row in analysis_indexes
        )
        composite = {
            (row[3], row[4])
            for row in eligibility_foreign_keys
            if row[2] == "work_order_analyses"
        }
        assert composite == {
            ("work_order_analysis_id", "id"),
            ("work_order_id", "work_order_id"),
        }
        for constraint in (
            "ck_scoring_schema_version",
            "ck_scoring_configuration_version",
            "ck_scoring_input_hash",
            "ck_scoring_input_json",
            "ck_scoring_output_json",
            "ck_scoring_candidate_count",
            "ck_scoring_eligible_count",
            "ck_scoring_ineligible_count",
            "ck_scoring_partition_count",
            "ck_scoring_top_consistency",
            "ck_scoring_top_score_shape",
            "uq_scoring_eligibility_configuration_input",
        ):
            assert constraint in scoring_sql
        assert {
            (row[2], row[3], row[4]) for row in scoring_foreign_keys
        } == {
            (
                "configuration_versions",
                "configuration_version",
                "version",
            ),
            (
                "eligibility_evaluation_sets",
                "eligibility_evaluation_set_id",
                "id",
            ),
        }
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE eligibility_evaluation_sets SET schema_version = 'v2'",
        (
            "UPDATE eligibility_evaluation_sets "
            "SET configuration_version = 'eligibility-alt'"
        ),
        "UPDATE eligibility_evaluation_sets SET input_hash = 'invalid'",
        "UPDATE eligibility_evaluation_sets SET input_json = 'invalid'",
        "UPDATE eligibility_evaluation_sets SET output_json = 'invalid'",
        "UPDATE eligibility_evaluation_sets SET candidate_count = -1",
        "UPDATE eligibility_evaluation_sets SET eligible_count = 1",
        "UPDATE eligibility_evaluation_sets SET ineligible_count = 1",
        "UPDATE eligibility_evaluation_sets SET no_feasible_candidates = 2",
        "UPDATE eligibility_evaluation_sets SET no_feasible_candidates = 0",
    ],
)
def test_eligibility_migration_checks_reject_invalid_rows(
    tmp_path: Path,
    statement: str,
) -> None:
    from sqlalchemy.exc import IntegrityError

    from app.adapters.persistence.database import create_sqlite_engine
    from app.migrations.runtime import upgrade_to_head

    database_path = tmp_path / "eligibility-checks.db"
    upgrade_to_head(database_path)
    engine = create_sqlite_engine(database_path)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO work_orders "
                    "(id, schema_version, raw_input_json, incident_text, "
                    "address, zone, context_json, created_at) VALUES "
                    "('11111111-1111-4111-8111-111111111111', 'v1', '{}', "
                    "'incident', 'address', 'zone', 'null', "
                    "'2026-07-28T00:00:00Z')"
                )
            )
            for version in (
                "analysis-v1",
                "eligibility-v1",
                "eligibility-alt",
            ):
                connection.execute(
                    text(
                        "INSERT INTO configuration_versions "
                        "(version, contract_version, registry_json, "
                        "registry_sha256, created_at) VALUES "
                        "(:version, 'v1', '{}', :digest, "
                        "'2026-07-28T00:00:00Z')"
                    ),
                    {"version": version, "digest": "a" * 64},
                )
            connection.execute(
                text(
                    "INSERT INTO work_order_analyses "
                    "(id, work_order_id, schema_version, "
                    "configuration_version, input_hash, output_json, "
                    "category, priority, sla_target_minutes, "
                    "required_certifications_json, "
                    "estimated_service_duration_minutes, created_at) VALUES "
                    "('22222222-2222-4222-8222-222222222222', "
                    "'11111111-1111-4111-8111-111111111111', 'v1', "
                    "'analysis-v1', :digest, '{}', 'gas', 5, 60, '[]', 90, "
                    "'2026-07-28T00:00:00Z')"
                ),
                {"digest": "b" * 64},
            )
            connection.execute(
                text(
                    "INSERT INTO eligibility_evaluation_sets "
                    "(id, work_order_id, work_order_analysis_id, "
                    "schema_version, configuration_version, input_hash, "
                    "input_json, output_json, candidate_count, eligible_count, "
                    "ineligible_count, no_feasible_candidates, created_at) "
                    "VALUES ('33333333-3333-4333-8333-333333333333', "
                    "'11111111-1111-4111-8111-111111111111', "
                    "'22222222-2222-4222-8222-222222222222', 'v1', "
                    "'eligibility-v1', :digest, '{}', '{}', 0, 0, 0, 1, "
                    "'2026-07-28T00:00:00Z')"
                ),
                {"digest": "c" * 64},
            )
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(statement))
    finally:
        engine.dispose()


def _insert_empty_scoring_evidence(connection) -> None:
    connection.execute(
        text(
            "INSERT INTO work_orders "
            "(id, schema_version, raw_input_json, incident_text, address, "
            "zone, context_json, created_at) VALUES "
            "('11111111-1111-4111-8111-111111111111', 'v1', '{}', "
            "'incident', 'address', 'zone', 'null', "
            "'2026-07-28T00:00:00Z')"
        )
    )
    for version in (
        "analysis-v1",
        "eligibility-v1",
        "scoring-v1",
        "scoring-alt",
    ):
        connection.execute(
            text(
                "INSERT INTO configuration_versions "
                "(version, contract_version, registry_json, "
                "registry_sha256, created_at) VALUES "
                "(:version, 'v1', '{}', :digest, "
                "'2026-07-28T00:00:00Z')"
            ),
            {"version": version, "digest": "a" * 64},
        )
    connection.execute(
        text(
            "INSERT INTO work_order_analyses "
            "(id, work_order_id, schema_version, configuration_version, "
            "input_hash, output_json, category, priority, "
            "sla_target_minutes, required_certifications_json, "
            "estimated_service_duration_minutes, created_at) VALUES "
            "('22222222-2222-4222-8222-222222222222', "
            "'11111111-1111-4111-8111-111111111111', 'v1', "
            "'analysis-v1', :digest, '{}', 'gas', 5, 60, '[]', 90, "
            "'2026-07-28T00:00:00Z')"
        ),
        {"digest": "b" * 64},
    )
    connection.execute(
        text(
            "INSERT INTO eligibility_evaluation_sets "
            "(id, work_order_id, work_order_analysis_id, schema_version, "
            "configuration_version, input_hash, input_json, output_json, "
            "candidate_count, eligible_count, ineligible_count, "
            "no_feasible_candidates, created_at) VALUES "
            "('33333333-3333-4333-8333-333333333333', "
            "'11111111-1111-4111-8111-111111111111', "
            "'22222222-2222-4222-8222-222222222222', 'v1', "
            "'eligibility-v1', :digest, '{}', '{}', 0, 0, 0, 1, "
            "'2026-07-28T00:00:00Z')"
        ),
        {"digest": "c" * 64},
    )
    connection.execute(
        text(
            "INSERT INTO scoring_evaluation_sets "
            "(id, eligibility_evaluation_set_id, schema_version, "
            "configuration_version, input_hash, input_json, output_json, "
            "candidate_count, eligible_count, ineligible_count, "
            "top_technician_id, top_objective_score, created_at) VALUES "
            "('44444444-4444-4444-8444-444444444444', "
            "'33333333-3333-4333-8333-333333333333', 'v1', "
            "'scoring-v1', :digest, '{}', '{}', 0, 0, 0, NULL, NULL, "
            "'2026-07-28T00:00:00Z')"
        ),
        {"digest": "d" * 64},
    )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE scoring_evaluation_sets SET schema_version = 'v2'",
        (
            "UPDATE scoring_evaluation_sets "
            "SET configuration_version = 'scoring-alt'"
        ),
        "UPDATE scoring_evaluation_sets SET input_hash = 'invalid'",
        "UPDATE scoring_evaluation_sets SET input_json = 'invalid'",
        "UPDATE scoring_evaluation_sets SET output_json = 'invalid'",
        "UPDATE scoring_evaluation_sets SET candidate_count = -1",
        "UPDATE scoring_evaluation_sets SET eligible_count = 1",
        "UPDATE scoring_evaluation_sets SET ineligible_count = 1",
        (
            "UPDATE scoring_evaluation_sets SET "
            "top_technician_id = '55555555-5555-4555-8555-555555555555'"
        ),
        "UPDATE scoring_evaluation_sets SET top_objective_score = '50'",
    ],
)
def test_scoring_migration_checks_reject_invalid_rows(
    tmp_path: Path,
    statement: str,
) -> None:
    from sqlalchemy.exc import IntegrityError

    from app.adapters.persistence.database import create_sqlite_engine
    from app.migrations.runtime import upgrade_to_head

    database_path = tmp_path / "scoring-checks.db"
    upgrade_to_head(database_path)
    engine = create_sqlite_engine(database_path)
    try:
        with engine.begin() as connection:
            _insert_empty_scoring_evidence(connection)
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(statement))
    finally:
        engine.dispose()
