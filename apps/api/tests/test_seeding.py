from app.seeding import curated_seed_rows, seed_curated_functions


class FakeTable:
    def __init__(self) -> None:
        self.rows = []
        self.conflict = ""

    def upsert(self, payload, on_conflict):  # type: ignore[no-untyped-def]
        self.rows = payload
        self.conflict = on_conflict
        return self

    def execute(self):  # type: ignore[no-untyped-def]
        return self


class FakeClient:
    def __init__(self) -> None:
        self.table_client = FakeTable()

    def table(self, name):  # type: ignore[no-untyped-def]
        assert name == "functions"
        return self.table_client


def test_curated_seed_rows_are_published_and_reproducible():
    rows = curated_seed_rows()
    assert len(rows) >= 6
    assert all(row["status"] == "published" and row["moderation_status"] == "allowed" for row in rows)
    assert all(row["code_hash"] and row["visualization_spec"]["schema_version"] == 1 for row in rows)


def test_seed_upserts_by_normalized_code_and_analyzer_version():
    client = FakeClient()
    assert seed_curated_functions(client) == len(client.table_client.rows)
    assert client.table_client.conflict == "code_hash,analyzer_version"
