# app.py
from flask import Flask, render_template, request, redirect, session, jsonify
import os
import random
import re
import sqlite3
from datetime import datetime, timedelta


app = Flask(__name__)
app.secret_key = "your_very_secret_key_12345"
DB_PATH = "/tmp/database.db"

DEMO_EMAILS = [
    "training.user01@example.com",
    "awareness.participant@example.com",
    "demo.learner@example.com",
    "simulated.employee@example.com",
    "practice.user@example.com",
]

DEMO_COUNTRIES = [
    ("Local Network", "Localhost"),
    ("United States", "Austin"),
    ("Germany", "Berlin"),
    ("Canada", "Toronto"),
    ("Iraq", "Baghdad"),
]

DEMO_DEVICES = [
    ("Desktop", "Windows", "Chrome"),
    ("Desktop", "macOS", "Safari"),
    ("Desktop", "Linux", "Firefox"),
    ("Mobile", "Android", "Chrome"),
    ("Mobile", "iOS", "Safari"),
]


def ensure_db_directory():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def table_exists(conn, table_name):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone() is not None


def get_table_columns(conn, table_name):
    if not table_exists(conn, table_name):
        return set()
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}


def log_audit(conn, action, details):
    conn.execute(
        """
        INSERT INTO audit_logs (action, details, created_at)
        VALUES (?, ?, ?)
        """,
        (action, details, datetime.now().isoformat()),
    )


def migrate_legacy_credentials_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            simulated_password TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            time_spent_sec REAL,
            os_name TEXT,
            browser_name TEXT,
            timestamp TEXT NOT NULL
        );
        """
    )
    existing_columns = get_table_columns(conn, "credentials")
    if "simulated_password" not in existing_columns:
        conn.execute("ALTER TABLE credentials ADD COLUMN simulated_password TEXT")
        existing_columns.add("simulated_password")
    if "password" in existing_columns:
        conn.execute(
            """
            UPDATE credentials
            SET simulated_password = COALESCE(simulated_password, 'training_input_redacted')
            WHERE simulated_password IS NULL OR simulated_password = ''
            """
        )
    conn.execute(
        """
        UPDATE credentials
        SET simulated_password = COALESCE(simulated_password, 'training_input_redacted')
        WHERE simulated_password IS NULL OR simulated_password = ''
        """
    )


def create_migration_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT,
            device_type TEXT,
            operating_system TEXT,
            browser TEXT,
            country TEXT,
            city TEXT,
            first_seen TEXT,
            last_seen TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id INTEGER,
            email TEXT,
            training_input TEXT,
            email_started_at TEXT,
            submitted_at TEXT,
            time_spent_seconds INTEGER,
            created_at TEXT,
            FOREIGN KEY (visitor_id) REFERENCES visitors (id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            details TEXT,
            created_at TEXT
        )
        """
    )


def migrate_sessions_schema(conn):
    columns = get_table_columns(conn, "sessions")
    if "submitted_at" not in columns and "password_submitted_at" in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN submitted_at TEXT")
        conn.execute(
            """
            UPDATE sessions
            SET submitted_at = COALESCE(submitted_at, password_submitted_at)
            WHERE submitted_at IS NULL OR submitted_at = ''
            """
        )
    if "training_input" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN training_input TEXT")
    conn.execute(
        """
        UPDATE sessions
        SET training_input = COALESCE(training_input, 'training_input_submitted')
        WHERE training_input IS NULL OR training_input = ''
        """
    )


def apply_migration(conn, name, migration_func):
    existing = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE name = ?",
        (name,),
    ).fetchone()
    if existing:
        return
    migration_func(conn)
    conn.execute(
        "INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)",
        (name, datetime.now().isoformat()),
    )


def backfill_analytics_tables(conn):
    if not table_exists(conn, "credentials"):
        return

    conn.execute(
        """
        INSERT INTO visitors (
            ip_address, device_type, operating_system, browser, country, city, first_seen, last_seen
        )
        SELECT
            COALESCE(credentials.ip_address, 'demo.local'),
            CASE WHEN credentials.os_name LIKE '%(Mobile)%' THEN 'Mobile' ELSE 'Desktop' END,
            COALESCE(credentials.os_name, 'Unknown'),
            COALESCE(credentials.browser_name, 'Unknown'),
            'Imported Demo Data',
            'Legacy Dataset',
            MIN(credentials.timestamp),
            MAX(credentials.timestamp)
        FROM credentials
        WHERE NOT EXISTS (
            SELECT 1 FROM visitors
            WHERE visitors.ip_address = COALESCE(credentials.ip_address, 'demo.local')
        )
        GROUP BY COALESCE(credentials.ip_address, 'demo.local')
        """
    )
    conn.execute(
        """
        INSERT INTO sessions (
            visitor_id, email, training_input, email_started_at, submitted_at, time_spent_seconds, created_at
        )
        SELECT
            visitors.id,
            'legacy-demo@example.com',
            'training_input_imported',
            credentials.timestamp,
            credentials.timestamp,
            CAST(COALESCE(credentials.time_spent_sec, 0) AS INTEGER),
            credentials.timestamp
        FROM credentials
        LEFT JOIN visitors ON visitors.ip_address = COALESCE(credentials.ip_address, 'demo.local')
        WHERE NOT EXISTS (
            SELECT 1 FROM sessions
            WHERE sessions.created_at = credentials.timestamp
              AND sessions.visitor_id = visitors.id
        )
        """
    )
    log_audit(conn, "legacy_backfill", "Imported legacy rows into demo analytics tables")


def seed_demo_records(conn):
    if conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] > 0:
        return

    now = datetime.now()
    for index in range(18):
        email = DEMO_EMAILS[index % len(DEMO_EMAILS)]
        device_type, operating_system, browser = DEMO_DEVICES[index % len(DEMO_DEVICES)]
        country, city = DEMO_COUNTRIES[index % len(DEMO_COUNTRIES)]
        ip_address = f"demo-net-{index % 6 + 1}"
        created_at = (now - timedelta(days=index % 7, hours=index * 2)).replace(microsecond=0)
        first_seen = (created_at - timedelta(minutes=3)).isoformat()
        submitted_at = created_at.isoformat()
        time_spent = 18 + (index * 7) % 95

        visitor = conn.execute(
            """
            SELECT id FROM visitors
            WHERE ip_address = ? AND device_type = ? AND operating_system = ? AND browser = ?
            """,
            (ip_address, device_type, operating_system, browser),
        ).fetchone()
        if visitor:
            visitor_id = visitor[0]
            conn.execute(
                """
                UPDATE visitors
                SET last_seen = ?
                WHERE id = ?
                """,
                (submitted_at, visitor_id),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO visitors (
                    ip_address, device_type, operating_system, browser, country, city, first_seen, last_seen
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ip_address, device_type, operating_system, browser, country, city, first_seen, submitted_at),
            )
            visitor_id = cursor.lastrowid

        conn.execute(
            """
            INSERT INTO sessions (
                visitor_id, email, training_input, email_started_at, submitted_at, time_spent_seconds, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                visitor_id,
                email,
                "training_input_submitted",
                first_seen,
                submitted_at,
                time_spent,
                submitted_at,
            ),
        )

    log_audit(conn, "demo_seeded", "Seeded synthetic training analytics records")


def init_db():
    ensure_db_directory()
    with sqlite3.connect(DB_PATH) as conn:
        migrate_legacy_credentials_schema(conn)
        create_migration_tables(conn)
        migrate_sessions_schema(conn)
        apply_migration(conn, "backfill_analytics_from_credentials", backfill_analytics_tables)
        apply_migration(conn, "seed_demo_records", seed_demo_records)
        conn.commit()


def get_db_connection():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_demo_identity():
    identity_seed = random.randint(1000, 9999)
    return f"training.participant{identity_seed}@example.com"


def add_demo_training_session():
    started_at = session.pop("email_started_at", None)
    submitted_at = datetime.now().replace(microsecond=0)
    if started_at:
        try:
            started_dt = datetime.fromisoformat(started_at)
            time_spent = int((submitted_at - started_dt).total_seconds())
        except ValueError:
            started_dt = submitted_at - timedelta(seconds=42)
            time_spent = 42
    else:
        started_dt = submitted_at - timedelta(seconds=42)
        time_spent = 42

    email = get_demo_identity()
    device_type, operating_system, browser = random.choice(DEMO_DEVICES)
    country, city = random.choice(DEMO_COUNTRIES)
    ip_address = f"demo-net-{random.randint(1, 9)}"

    with get_db_connection() as conn:
        visitor = conn.execute(
            """
            SELECT id, first_seen FROM visitors
            WHERE ip_address = ? AND device_type = ? AND operating_system = ? AND browser = ?
            """,
            (ip_address, device_type, operating_system, browser),
        ).fetchone()
        if visitor:
            visitor_id = visitor["id"]
            conn.execute(
                """
                UPDATE visitors
                SET country = ?, city = ?, last_seen = ?
                WHERE id = ?
                """,
                (country, city, submitted_at.isoformat(), visitor_id),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO visitors (
                    ip_address, device_type, operating_system, browser, country, city, first_seen, last_seen
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ip_address,
                    device_type,
                    operating_system,
                    browser,
                    country,
                    city,
                    started_dt.isoformat(),
                    submitted_at.isoformat(),
                ),
            )
            visitor_id = cursor.lastrowid

        conn.execute(
            """
            INSERT INTO sessions (
                visitor_id, email, training_input, email_started_at, submitted_at, time_spent_seconds, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                visitor_id,
                email,
                "training_input_submitted",
                started_dt.isoformat(),
                submitted_at.isoformat(),
                max(time_spent, 1),
                submitted_at.isoformat(),
            ),
        )
        conn.execute(
            """
            INSERT INTO credentials (
                username, simulated_password, ip_address, user_agent, time_spent_sec, os_name, browser_name, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email,
                "training_input_submitted",
                ip_address,
                "Synthetic Training Browser",
                max(time_spent, 1),
                f"{operating_system} ({device_type})",
                browser,
                submitted_at.isoformat(),
            ),
        )
        log_audit(conn, "new_training_session", "Added a synthetic training session record")
        conn.commit()


def build_filters():
    return {
        "search": request.args.get("search", "").strip(),
        "ip": request.args.get("ip", "").strip(),
        "device": request.args.get("device", "").strip(),
        "country": request.args.get("country", "").strip(),
        "date": request.args.get("date", "").strip(),
    }


def fetch_session_rows(conn, filters=None):
    filters = filters or {}
    query = """
        SELECT
            sessions.id,
            sessions.email,
            sessions.training_input,
            visitors.ip_address,
            visitors.device_type,
            visitors.operating_system,
            visitors.browser,
            visitors.country,
            visitors.city,
            sessions.time_spent_seconds,
            sessions.created_at,
            sessions.submitted_at
        FROM sessions
        LEFT JOIN visitors ON visitors.id = sessions.visitor_id
        WHERE 1 = 1
    """
    params = []

    if filters.get("search"):
        query += " AND LOWER(sessions.email) LIKE ?"
        params.append(f"%{filters['search'].lower()}%")
    if filters.get("ip"):
        query += " AND LOWER(COALESCE(visitors.ip_address, '')) LIKE ?"
        params.append(f"%{filters['ip'].lower()}%")
    if filters.get("device"):
        query += " AND visitors.device_type = ?"
        params.append(filters["device"])
    if filters.get("country"):
        query += " AND visitors.country = ?"
        params.append(filters["country"])
    if filters.get("date"):
        query += " AND DATE(sessions.created_at) = ?"
        params.append(filters["date"])

    query += " ORDER BY sessions.created_at DESC"
    return conn.execute(query, params).fetchall()


def build_stats_payload(conn):
    today = datetime.now().date().isoformat()
    week_cutoff = (datetime.now() - timedelta(days=7)).isoformat()

    total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    today_sessions = conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE DATE(created_at) = ?",
        (today,),
    ).fetchone()[0]
    week_sessions = conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE created_at >= ?",
        (week_cutoff,),
    ).fetchone()[0]
    mobile_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM sessions
        LEFT JOIN visitors ON visitors.id = sessions.visitor_id
        WHERE visitors.device_type = 'Mobile'
        """
    ).fetchone()[0]
    desktop_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM sessions
        LEFT JOIN visitors ON visitors.id = sessions.visitor_id
        WHERE visitors.device_type = 'Desktop'
        """
    ).fetchone()[0]

    def grouped(query):
        return [
            {"label": row[0] or "Unknown", "count": row[1]}
            for row in conn.execute(query).fetchall()
        ]

    visitors_per_day = [
        {"date": row[0], "count": row[1]}
        for row in conn.execute(
            """
            SELECT DATE(created_at) AS day, COUNT(*)
            FROM sessions
            GROUP BY day
            ORDER BY day ASC
            """
        ).fetchall()
    ]

    return {
        "total_sessions": total_sessions,
        "today_sessions": today_sessions,
        "week_sessions": week_sessions,
        "mobile_count": mobile_count,
        "desktop_count": desktop_count,
        "top_browsers": grouped(
            """
            SELECT visitors.browser, COUNT(*)
            FROM sessions
            LEFT JOIN visitors ON visitors.id = sessions.visitor_id
            GROUP BY visitors.browser
            ORDER BY COUNT(*) DESC, visitors.browser ASC
            LIMIT 5
            """
        ),
        "top_operating_systems": grouped(
            """
            SELECT visitors.operating_system, COUNT(*)
            FROM sessions
            LEFT JOIN visitors ON visitors.id = sessions.visitor_id
            GROUP BY visitors.operating_system
            ORDER BY COUNT(*) DESC, visitors.operating_system ASC
            LIMIT 5
            """
        ),
        "top_countries": grouped(
            """
            SELECT visitors.country, COUNT(*)
            FROM sessions
            LEFT JOIN visitors ON visitors.id = sessions.visitor_id
            GROUP BY visitors.country
            ORDER BY COUNT(*) DESC, visitors.country ASC
            LIMIT 5
            """
        ),
        "visitors_per_day": visitors_per_day,
    }


@app.route("/")
def home():
    session["email_started_at"] = datetime.now().replace(microsecond=0).isoformat()
    return render_template("login_email.html", error=None)


@app.route("/submit_email", methods=["POST"])
def submit_email():
    provided_value = request.form.get("username", "")
    email_phone_regex = r"(^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$)|(^\+?\d{7,15}$)"

    if re.match(email_phone_regex, provided_value):
        session["demo_flow_ready"] = True
        demo_identity = session.get("demo_identity")
        if not demo_identity:
            demo_identity = get_demo_identity()
            session["demo_identity"] = demo_identity
        return render_template("login_password.html", username=demo_identity)

    error_message = "Please enter a valid email address or phone number."
    return render_template("login_email.html", error=error_message)


@app.route("/submit_password", methods=["POST"])
def submit_password():
    init_db()
    if not session.get("demo_flow_ready"):
        return redirect("/")

    try:
        add_demo_training_session()
    except Exception as exc:
        print(f"[ERROR] Could not create demo session: {exc}")
        return "Unable to process your training request right now.", 500

    session.pop("demo_flow_ready", None)
    session.pop("demo_identity", None)
    return redirect("https://www.google.com")


@app.route("/results")
def results():
    with get_db_connection() as conn:
        log_audit(conn, "dashboard_opened", "Opened the demo analytics dashboard")
        conn.commit()
    return render_template("results.html")


@app.route("/api/stats")
def api_stats():
    try:
        with get_db_connection() as conn:
            stats = build_stats_payload(conn)
            log_audit(conn, "api_stats_viewed", "Viewed demo statistics")
            conn.commit()
        return jsonify(stats)
    except Exception as exc:
        print(f"[ERROR] Could not load stats: {exc}")
        return jsonify({"error": "Unable to load demo stats"}), 500


@app.route("/api/data")
def api_data():
    try:
        filters = build_filters()
        with get_db_connection() as conn:
            rows = [dict(row) for row in fetch_session_rows(conn, filters)]
            log_audit(conn, "api_data_viewed", f"Viewed demo session data with filters: {filters}")
            conn.commit()
        return jsonify(rows)
    except Exception as exc:
        print(f"[ERROR] Could not load session data: {exc}")
        return jsonify({"error": "Unable to load demo session data"}), 500


@app.route("/api/audit-logs")
def api_audit_logs():
    try:
        with get_db_connection() as conn:
            rows = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT id, action, details, created_at
                    FROM audit_logs
                    ORDER BY created_at DESC
                    LIMIT 12
                    """
                ).fetchall()
            ]
            log_audit(conn, "api_audit_logs_viewed", "Viewed recent demo audit logs")
            conn.commit()
        return jsonify(rows)
    except Exception as exc:
        print(f"[ERROR] Could not load audit logs: {exc}")
        return jsonify({"error": "Unable to load demo audit logs"}), 500


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
