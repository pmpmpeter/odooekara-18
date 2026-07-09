import sys

sys.path.insert(0, "/opt/odoo18/odoo18-server")

import odoo
from odoo import api, SUPERUSER_ID

# Update this if your config path is different
odoo.tools.config.parse_config([
    "--config=/opt/odoo18/ekara.conf"
])

registry = odoo.registry("ekara_18_test")

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    print("Reading old budget positions...")

    cr.execute("""
        SELECT
            id,
            name,
            company_id,
            sequence,
            is_locked,
            budget_type,
            budget_category,
            state,
            create_uid,
            write_uid,
            create_date,
            write_date
        FROM account_budget_post
        ORDER BY id
    """)

    rows = cr.dictfetchall()

    print(f"Found {len(rows)} records")

    for row in rows:

        # Skip if already migrated
        cr.execute("""
            SELECT 1
            FROM account_report_budget
            WHERE id=%s
        """, (row["id"],))

        if cr.fetchone():
            print(f"Skipping ID {row['id']}")
            continue

        print(f"Migrating ID {row['id']} : {row['name']}")

        cr.execute("""
            INSERT INTO account_report_budget (
                id,
                name,
                company_id,
                sequence,
                is_locked,
                budget_type,
                budget_category,
                state,
                create_uid,
                write_uid,
                create_date,
                write_date
            )
            VALUES (
                %(id)s,
                %(name)s,
                %(company_id)s,
                %(sequence)s,
                %(is_locked)s,
                %(budget_type)s,
                %(budget_category)s,
                %(state)s,
                %(create_uid)s,
                %(write_uid)s,
                %(create_date)s,
                %(write_date)s
            )
        """, row)

    # Reset sequence
    cr.execute("""
        SELECT setval(
            pg_get_serial_sequence('account_report_budget','id'),
            COALESCE((SELECT MAX(id) FROM account_report_budget),1)
        )
    """)

    cr.commit()

print("===================================")
print("Budget migration completed.")
print("===================================")
# source venv/bin/activate
# python3 migrate_budget.py