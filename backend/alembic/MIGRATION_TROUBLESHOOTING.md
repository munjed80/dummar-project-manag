# Alembic migration troubleshooting

## `KeyError: '19'` when running migrations

This error usually means a migration referenced `down_revision = "19"` while this project uses zero-padded revision ids (`"019"`, `"020"`, `"021"`).

Use this chain for the latest migrations in this repo:

- `018_sync_notification_enum_values.py` → `revision = "018"`
- `019_add_investment_property_attachments.py` → `down_revision = "018"`
- `020_add_more_investment_contract_attachments.py` → `down_revision = "019"`
- `021_add_internal_messages.py` → `down_revision = "020"`

So in migration `021`, the correct value is:

```py
 down_revision = "020"
```

## Verify the graph

From `backend/` run:

```bash
alembic history
alembic heads
```

If you still get errors, inspect `alembic_version` in the database and ensure it matches an existing migration revision id in `alembic/versions`.
