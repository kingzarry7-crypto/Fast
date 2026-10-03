"""api.py bootstrap: load known-good source + patches. Cache bust v3."""
import os
import urllib.request

GOOD_URL = "https://raw.githubusercontent.com/kingzarry7-crypto/Fast/d53e44a4f5f511f7660bd02f3db0852a8cb36462/api.py"
CACHE_NAME = "_api_good_cache_v3.py"

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
        )
        log = ns.get("logger")
        if log:
            log.info("admin_stats_fix installed")
    except Exception as e:
        log = ns.get("logger")
        if log:
            log.warning("admin stats fix install: %s", type(e).__name__)

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
        log = ns.get("logger")
        if log:
            log.warning("email broadcast install: %s", type(e).__name__)
    g = globals()
    for k, v in ns.items():
        if not k.startswith("__"):
            g[k] = v

_load_good()
