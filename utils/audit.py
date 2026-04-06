def log_audit(
    cursor,
    table_name,
    record_id,
    column_name,
    old_value,
    new_value,
    action_type,
    user_id,
    user_role,
    module,
    impact
):
    """
    Generic audit logging function
    """

    query = """
        INSERT INTO audit_logs (
            table_name,
            record_id,
            column_name,
            old_value,
            new_value,
            action_type,
            changed_by,
            user_role,
            module_name,
            impact_level
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    try:
        cursor.execute(query, (
            table_name,
            record_id,
            column_name,
            str(old_value) if old_value is not None else None,
            str(new_value) if new_value is not None else None,
            action_type,
            user_id,
            str(user_role),
            module,
            impact
        ))

    except Exception as e:
        # Fail-safe: audit should NEVER break main flow
        print("Audit Log Error:", e)