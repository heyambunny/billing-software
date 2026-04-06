import pandas as pd

def update_billing_totals(conn, billing_id):

    # -------- VENDOR TOTAL --------
    vendor_total = pd.read_sql("""
        SELECT COALESCE(SUM(amount),0) as total
        FROM vendor_expenses
        WHERE billing_entry_id = %s
    """, conn, params=(billing_id,)).iloc[0]["total"]

    # -------- CN TOTAL --------
    cn_total = pd.read_sql("""
        SELECT COALESCE(SUM(cn_amount),0) as total
        FROM credit_notes
        WHERE billing_entry_id = %s
    """, conn, params=(billing_id,)).iloc[0]["total"]

    # -------- BILLED AMOUNT --------
    billed_amount = pd.read_sql("""
        SELECT client_billed_amount
        FROM billing_entries
        WHERE id = %s
    """, conn, params=(billing_id,)).iloc[0]["client_billed_amount"]

    # -------- CALCULATION --------
    gross_margin = float(billed_amount) - float(vendor_total) - float(cn_total)

    # -------- UPDATE --------
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE billing_entries
        SET total_vendor_amount = %s,
            total_cn_amount = %s,
            gross_margin = %s
        WHERE id = %s
    """, (
        float(vendor_total),
        float(cn_total),
        float(gross_margin),
        billing_id
    ))

    conn.commit()