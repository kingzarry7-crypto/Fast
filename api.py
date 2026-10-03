"""api.py bootstrap: load known-good source + patches. Cache bust v4."""
import os
import urllib.request

GOOD_URL = "https://raw.githubusercontent.com/kingzarry7-crypto/Fast/d53e44a4f5f511f7660bd02f3db0852a8cb36462/api.py"
CACHE_NAME = "_api_good_cache_v4.py"

def _load_good():
    path = os.path.join(os.path.dirname(__file__), CACHE_NAME)
    if not os.path.isfile(path) or os.path.getsize(path) < 10000:
        with urllib.request.urlopen(GOOD_URL, timeout=60) as resp:
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    ns = {"__name__": "api", "__file__": path}
    exec(compile(code, path, "exec"), ns, ns)

    try:
        from admin_stats_fix import install_admin_stats_fix
        install_admin_stats_fix(
            ns["app"],
            require_admin=ns["_require_admin"],
            get_db_cursor=ns["get_db_cursor"],
            row_value=ns["_row_value"],
            ensure_billing_tables=ns.get("_ensure_billing_tables"),
            is_database_configured=ns.get("is_database_configured"),
            require_current_user=ns.get("_require_current_user"),
            is_admin_email=ns.get("_is_admin_email"),
            has_valid_admin_session=ns.get("_has_valid_admin_session"),
            admin_password=ns.get("ADMIN_PASSWORD") or "",
            admin_emails=ns.get("ADMIN_EMAILS"),
        )
        print("ADMIN_PATCHES_INSTALLED", flush=True)
    except Exception as e:
        print("ADMIN_PATCHES_FAILED", type(e).__name__, flush=True)

    try:
        from admin_email_broadcast import install_email_broadcast
        install_email_broadcast(
            ns["app"],
            require_admin=ns["_require_admin"],
            get_db_cursor=ns["get_db_cursor"],
            row_value=ns["_row_value"],
            send_email_resend=ns["_send_email_resend"],
            resend_api_key=ns["RESEND_API_KEY"],
            email_from=ns["EMAIL_FROM"],
        )
    except Exception as e:
        print("EMAIL_BROADCAST_INSTALL_FAILED", type(e).__name__, flush=True)
    g = globals()
    for k, v in ns.items():
        if not k.startswith("__"):
            g[k] = v

_load_good()
