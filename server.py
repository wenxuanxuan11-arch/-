import hashlib
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data")).resolve()
DB_PATH = DATA_DIR / "registry.db"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
ADMIN_STUDENT_ID = os.getenv("ADMIN_STUDENT_ID", "240520230").strip()
ADMIN_NAME = os.getenv("ADMIN_NAME", "宣文轩").strip()
SESSION_DAYS = max(1, int(os.getenv("SESSION_DAYS", "7")))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
MAX_BODY_BYTES = 24 * 1024 * 1024
SESSION_COOKIE = "wj_session"
CHINA_TZ = timezone(timedelta(hours=8))


AREA_OPTIONS = [
    "图书馆周边",
    "食堂周边",
    "宿舍区",
    "教学楼",
    "体育馆",
    "湖畔步道",
    "校门附近",
    "其他",
]
GENDER_OPTIONS = {"未知", "公", "母"}
AGE_OPTIONS = {"幼猫", "青年猫", "成猫", "老年猫", "未知"}
STATUS_OPTIONS = {"常驻", "偶遇", "医疗观察", "待领养", "已领养", "失踪"}
STERILIZED_OPTIONS = {"未知", "已绝育", "未绝育"}
VACCINATED_OPTIONS = {"未知", "已疫苗", "未疫苗"}
SAFE_PHOTO_RE = re.compile(r"^data:image/(jpeg|jpg|png|webp);base64,", re.IGNORECASE)
STUDENT_ID_RE = re.compile(r"^\d{9}$")
NOTE_TONES = {"leaf", "sun", "sky", "rose", "paper"}


SAMPLE_CATS = [
    {
        "id": "sample-001",
        "registryNo": "WJIT-CAT-001",
        "photoData": "",
        "name": "小橘",
        "gender": "公",
        "coat": "橘白，左耳尖有白毛",
        "age": "成猫",
        "campusArea": "图书馆周边",
        "location": "图书馆东侧台阶",
        "status": "常驻",
        "sterilized": "已绝育",
        "vaccinated": "已疫苗",
        "caretaker": "爱猫社",
        "notes": "亲人，晚间常在台阶附近休息，喜欢干粮和清水。",
        "createdAt": "2026-05-26T10:00:00.000Z",
        "updatedAt": "2026-05-26T10:00:00.000Z",
    },
    {
        "id": "sample-002",
        "registryNo": "WJIT-CAT-002",
        "photoData": "",
        "name": "墨点",
        "gender": "母",
        "coat": "黑白奶牛，鼻尖有黑点",
        "age": "青年猫",
        "campusArea": "食堂周边",
        "location": "二食堂后门绿化带",
        "status": "医疗观察",
        "sterilized": "未绝育",
        "vaccinated": "未知",
        "caretaker": "后勤志愿组",
        "notes": "最近右后腿疑似受伤，行动稍慢，需要持续观察。",
        "createdAt": "2026-05-27T08:30:00.000Z",
        "updatedAt": "2026-05-27T08:30:00.000Z",
    },
    {
        "id": "sample-003",
        "registryNo": "WJIT-CAT-003",
        "photoData": "",
        "name": "栗子",
        "gender": "未知",
        "coat": "狸花，尾巴末端偏黑",
        "age": "幼猫",
        "campusArea": "宿舍区",
        "location": "南区宿舍楼下",
        "status": "偶遇",
        "sterilized": "未知",
        "vaccinated": "未疫苗",
        "caretaker": "宿管阿姨",
        "notes": "胆小，常跟另一只狸花幼猫一起出现，建议先记录出现时间。",
        "createdAt": "2026-05-28T12:00:00.000Z",
        "updatedAt": "2026-05-28T12:00:00.000Z",
    },
    {
        "id": "sample-004",
        "registryNo": "WJIT-CAT-004",
        "photoData": "",
        "name": "湖边白",
        "gender": "母",
        "coat": "白猫，头顶有浅灰斑",
        "age": "成猫",
        "campusArea": "湖畔步道",
        "location": "圆形建筑外侧湖边",
        "status": "待领养",
        "sterilized": "已绝育",
        "vaccinated": "已疫苗",
        "caretaker": "学生志愿者",
        "notes": "性格稳定，能接受抚摸，正在寻找合适领养人。",
        "createdAt": "2026-05-29T09:20:00.000Z",
        "updatedAt": "2026-05-29T09:20:00.000Z",
    },
]


def utc_now():
    return datetime.now(timezone.utc)


def iso_now():
    return utc_now().isoformat(timespec="milliseconds").replace("+00:00", "Z")


def iso_from_datetime(value):
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def db_connect():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with db_connect() as db:
        cats_table_exists = (
            db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'cats'").fetchone() is not None
        )
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cats (
                id TEXT PRIMARY KEY,
                registry_no TEXT NOT NULL UNIQUE,
                photo_data TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                gender TEXT NOT NULL,
                coat TEXT NOT NULL,
                age TEXT NOT NULL,
                campus_area TEXT NOT NULL,
                location TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                sterilized TEXT NOT NULL,
                vaccinated TEXT NOT NULL,
                caretaker TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by_student_id TEXT NOT NULL DEFAULT '',
                updated_by_name TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS visitors (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                login_count INTEGER NOT NULL DEFAULT 0,
                page_views INTEGER NOT NULL DEFAULT 0,
                last_ip TEXT NOT NULL DEFAULT '',
                last_user_agent TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                student_id TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                ip TEXT NOT NULL DEFAULT '',
                user_agent TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL,
                path TEXT NOT NULL DEFAULT '',
                ip TEXT NOT NULL DEFAULT '',
                user_agent TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                tone TEXT NOT NULL DEFAULT 'paper',
                author_student_id TEXT NOT NULL,
                author_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_access_logs_created_at
            ON access_logs(created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_access_logs_action
            ON access_logs(action);

            CREATE INDEX IF NOT EXISTS idx_sessions_expires_at
            ON sessions(expires_at);

            CREATE INDEX IF NOT EXISTS idx_notes_created_at
            ON notes(created_at DESC);
            """
        )

        sample_seeded = db.execute("SELECT value FROM app_meta WHERE key = 'sample_seeded'").fetchone()
        count = db.execute("SELECT COUNT(*) FROM cats").fetchone()[0]
        if not sample_seeded and not cats_table_exists and count == 0:
            for cat in SAMPLE_CATS:
                insert_cat(db, cat, "", "")
        if not sample_seeded:
            db.execute(
                "INSERT OR REPLACE INTO app_meta (key, value) VALUES ('sample_seeded', 'true')"
            )


def clean_text(value, max_length, required=False, field_name="字段"):
    text = str(value or "").strip()
    if required and not text:
        raise ValueError(f"{field_name}不能为空")
    if len(text) > max_length:
        raise ValueError(f"{field_name}不能超过 {max_length} 个字符")
    return text


def option_value(value, allowed, default):
    text = str(value or "").strip()
    return text if text in allowed else default


def clean_photo(value):
    text = str(value or "")
    if not text:
        return ""
    if len(text) > 4 * 1024 * 1024:
        raise ValueError("照片过大，请选择压缩后的图片")
    if not SAFE_PHOTO_RE.match(text):
        raise ValueError("照片格式不支持")
    return text


def normalize_cat(data):
    return {
        "photoData": clean_photo(data.get("photoData", "")),
        "name": clean_text(data.get("name"), 20, True, "姓名"),
        "gender": option_value(data.get("gender"), GENDER_OPTIONS, "未知"),
        "coat": clean_text(data.get("coat"), 32, True, "毛色特征"),
        "age": option_value(data.get("age"), AGE_OPTIONS, "未知"),
        "campusArea": clean_text(data.get("campusArea"), 32, True, "活动区域"),
        "location": clean_text(data.get("location"), 48, False, "固定点位"),
        "status": option_value(data.get("status"), STATUS_OPTIONS, "常驻"),
        "sterilized": option_value(data.get("sterilized"), STERILIZED_OPTIONS, "未知"),
        "vaccinated": option_value(data.get("vaccinated"), VACCINATED_OPTIONS, "未知"),
        "caretaker": clean_text(data.get("caretaker"), 24, False, "联系人"),
        "notes": clean_text(data.get("notes"), 240, False, "性格与备注"),
    }


def next_registry_no(db):
    rows = db.execute("SELECT registry_no FROM cats").fetchall()
    maximum = 0
    for row in rows:
        match = re.match(r"^WJIT-CAT-(\d+)$", row["registry_no"])
        if match:
            maximum = max(maximum, int(match.group(1)))
    return f"WJIT-CAT-{maximum + 1:03d}"


def insert_cat(db, cat, updated_by_student_id, updated_by_name):
    normalized = normalize_cat(cat)
    cat_id = clean_text(cat.get("id"), 80) or str(uuid.uuid4())
    registry_no = clean_text(cat.get("registryNo"), 32) or next_registry_no(db)
    created_at = clean_text(cat.get("createdAt"), 64) or iso_now()
    updated_at = clean_text(cat.get("updatedAt"), 64) or created_at
    db.execute(
        """
        INSERT INTO cats (
            id, registry_no, photo_data, name, gender, coat, age, campus_area,
            location, status, sterilized, vaccinated, caretaker, notes,
            created_at, updated_at, updated_by_student_id, updated_by_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cat_id,
            registry_no,
            normalized["photoData"],
            normalized["name"],
            normalized["gender"],
            normalized["coat"],
            normalized["age"],
            normalized["campusArea"],
            normalized["location"],
            normalized["status"],
            normalized["sterilized"],
            normalized["vaccinated"],
            normalized["caretaker"],
            normalized["notes"],
            created_at,
            updated_at,
            updated_by_student_id,
            updated_by_name,
        ),
    )
    return cat_id


def cat_from_row(row):
    return {
        "id": row["id"],
        "registryNo": row["registry_no"],
        "photoData": row["photo_data"],
        "name": row["name"],
        "gender": row["gender"],
        "coat": row["coat"],
        "age": row["age"],
        "campusArea": row["campus_area"],
        "location": row["location"],
        "status": row["status"],
        "sterilized": row["sterilized"],
        "vaccinated": row["vaccinated"],
        "caretaker": row["caretaker"],
        "notes": row["notes"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "updatedByStudentId": row["updated_by_student_id"],
        "updatedByName": row["updated_by_name"],
    }


def list_cats(db):
    rows = db.execute("SELECT * FROM cats ORDER BY updated_at DESC, registry_no ASC").fetchall()
    return [cat_from_row(row) for row in rows]


def normalize_note(data):
    content = clean_text(data.get("content"), 220, True, "便签内容")
    tone = clean_text(data.get("tone"), 16) or "paper"
    if tone not in NOTE_TONES:
        tone = "paper"
    return {"content": content, "tone": tone}


def note_from_row(row):
    return {
        "id": row["id"],
        "content": row["content"],
        "tone": row["tone"],
        "authorStudentId": row["author_student_id"],
        "authorName": row["author_name"],
        "createdAt": row["created_at"],
    }


def list_notes(db):
    rows = db.execute(
        """
        SELECT id, content, tone, author_student_id, author_name, created_at
        FROM notes
        ORDER BY created_at DESC
        LIMIT 200
        """
    ).fetchall()
    return [note_from_row(row) for row in rows]


def record_log(db, action, path="", user=None, ip="", user_agent=""):
    db.execute(
        """
        INSERT INTO access_logs (
            student_id, name, role, action, path, ip, user_agent, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user.get("studentId", "") if user else "",
            user.get("name", "") if user else "",
            user.get("role", "") if user else "",
            action,
            path,
            ip,
            user_agent,
            iso_now(),
        ),
    )


def visitor_upsert(db, user, ip, user_agent, login=False, page_view=False):
    now = iso_now()
    db.execute(
        """
        INSERT INTO visitors (
            student_id, name, role, first_seen, last_seen, login_count,
            page_views, last_ip, last_user_agent
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_id) DO UPDATE SET
            name = excluded.name,
            role = excluded.role,
            last_seen = excluded.last_seen,
            login_count = visitors.login_count + ?,
            page_views = visitors.page_views + ?,
            last_ip = excluded.last_ip,
            last_user_agent = excluded.last_user_agent
        """,
        (
            user["studentId"],
            user["name"],
            user["role"],
            now,
            now,
            1 if login else 0,
            1 if page_view else 0,
            ip,
            user_agent,
            1 if login else 0,
            1 if page_view else 0,
        ),
    )


class RegistryHandler(BaseHTTPRequestHandler):
    server_version = "WanjiangCatRegistry/1.0"

    def log_message(self, format_string, *args):
        print(f"{self.address_string()} - {format_string % args}")

    def client_ip(self):
        forwarded = self.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def user_agent(self):
        return self.headers.get("User-Agent", "")[:500]

    def send_json(self, status, payload, headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if headers:
            for name, value in headers.items():
                self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status, message):
        self.send_json(status, {"error": message})

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise ValueError("请求内容过大")
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("请求格式不正确") from error
        if not isinstance(data, dict):
            raise ValueError("请求格式不正确")
        return data

    def session_token(self):
        cookie_header = self.headers.get("Cookie", "")
        cookie = SimpleCookie()
        try:
            cookie.load(cookie_header)
        except Exception:
            return ""
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel else ""

    def current_user(self, touch=True):
        token = self.session_token()
        if not token:
            return None
        digest = token_hash(token)
        now = iso_now()
        with db_connect() as db:
            row = db.execute(
                """
                SELECT student_id, name, role, expires_at
                FROM sessions
                WHERE token_hash = ?
                """,
                (digest,),
            ).fetchone()
            if not row or row["expires_at"] <= now:
                db.execute("DELETE FROM sessions WHERE token_hash = ?", (digest,))
                return None
            user = {"studentId": row["student_id"], "name": row["name"], "role": row["role"]}
            if touch:
                db.execute(
                    "UPDATE sessions SET last_seen = ?, ip = ?, user_agent = ? WHERE token_hash = ?",
                    (now, self.client_ip(), self.user_agent(), digest),
                )
                visitor_upsert(db, user, self.client_ip(), self.user_agent())
            return user

    def require_user(self):
        user = self.current_user()
        if not user:
            self.send_error_json(HTTPStatus.UNAUTHORIZED, "请先登录")
            return None
        return user

    def require_admin(self):
        user = self.require_user()
        if not user:
            return None
        if user["role"] != "admin":
            self.send_error_json(HTTPStatus.FORBIDDEN, "只有管理员可以执行此操作")
            return None
        return user

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/health":
                self.send_json(HTTPStatus.OK, {"status": "ok", "time": iso_now()})
                return
            if path == "/api/session":
                self.handle_session()
                return
            if path == "/api/cats":
                self.handle_list_cats()
                return
            if path == "/api/notes":
                self.handle_list_notes()
                return
            if path == "/api/admin/stats":
                self.handle_admin_stats()
                return
            self.serve_static(path)
        except ValueError as error:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(error))
        except Exception as error:
            print(f"GET {path} failed: {error}")
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "服务器处理失败")

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            if path == "/api/login":
                self.handle_login()
                return
            if path == "/api/logout":
                self.handle_logout()
                return
            if path == "/api/heartbeat":
                self.handle_heartbeat()
                return
            if path == "/api/track":
                self.handle_track()
                return
            if path == "/api/cats":
                self.handle_create_cat()
                return
            if path == "/api/notes":
                self.handle_create_note()
                return
            if path == "/api/admin/import":
                self.handle_import()
                return
            if path == "/api/admin/restore-samples":
                self.handle_restore_samples()
                return
            self.send_error_json(HTTPStatus.NOT_FOUND, "接口不存在")
        except ValueError as error:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(error))
        except sqlite3.IntegrityError as error:
            print(f"POST {path} integrity error: {error}")
            self.send_error_json(HTTPStatus.CONFLICT, "档案编号或数据发生冲突")
        except Exception as error:
            print(f"POST {path} failed: {error}")
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "服务器处理失败")

    def do_PUT(self):
        path = urlparse(self.path).path
        try:
            match = re.fullmatch(r"/api/cats/([^/]+)", path)
            if match:
                self.handle_update_cat(unquote(match.group(1)))
                return
            self.send_error_json(HTTPStatus.NOT_FOUND, "接口不存在")
        except ValueError as error:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(error))
        except Exception as error:
            print(f"PUT {path} failed: {error}")
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "服务器处理失败")

    def do_DELETE(self):
        path = urlparse(self.path).path
        try:
            match = re.fullmatch(r"/api/cats/([^/]+)", path)
            if match:
                self.handle_delete_cat(unquote(match.group(1)))
                return
            match = re.fullmatch(r"/api/notes/([^/]+)", path)
            if match:
                self.handle_delete_note(unquote(match.group(1)))
                return
            self.send_error_json(HTTPStatus.NOT_FOUND, "接口不存在")
        except Exception as error:
            print(f"DELETE {path} failed: {error}")
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, "服务器处理失败")

    def handle_login(self):
        data = self.read_json()
        student_id = clean_text(data.get("studentId"), 9, True, "学号")
        name = clean_text(data.get("name"), 32, True, "姓名")
        if not STUDENT_ID_RE.fullmatch(student_id):
            raise ValueError("学号必须为 9 位数字")

        role = "admin" if student_id == ADMIN_STUDENT_ID and name == ADMIN_NAME else "viewer"
        user = {"studentId": student_id, "name": name, "role": role}
        token = secrets.token_urlsafe(32)
        digest = token_hash(token)
        created_at = iso_now()
        expires_at = iso_from_datetime(utc_now() + timedelta(days=SESSION_DAYS))
        ip = self.client_ip()
        user_agent = self.user_agent()

        with db_connect() as db:
            db.execute("DELETE FROM sessions WHERE expires_at <= ?", (created_at,))
            db.execute(
                """
                INSERT INTO sessions (
                    token_hash, student_id, name, role, created_at, last_seen,
                    expires_at, ip, user_agent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (digest, student_id, name, role, created_at, created_at, expires_at, ip, user_agent),
            )
            visitor_upsert(db, user, ip, user_agent, login=True, page_view=True)
            record_log(db, "login", "/api/login", user, ip, user_agent)
            record_log(db, "page_view", "/", user, ip, user_agent)

        cookie = f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_DAYS * 86400}"
        if COOKIE_SECURE:
            cookie += "; Secure"
        self.send_json(HTTPStatus.OK, {"user": user}, {"Set-Cookie": cookie})

    def handle_logout(self):
        user = self.current_user(touch=False)
        token = self.session_token()
        with db_connect() as db:
            if token:
                db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash(token),))
            if user:
                record_log(db, "logout", "/api/logout", user, self.client_ip(), self.user_agent())
        cookie = f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
        if COOKIE_SECURE:
            cookie += "; Secure"
        self.send_json(HTTPStatus.OK, {"ok": True}, {"Set-Cookie": cookie})

    def handle_session(self):
        user = self.current_user()
        if not user:
            self.send_error_json(HTTPStatus.UNAUTHORIZED, "请先登录")
            return
        with db_connect() as db:
            visitor_upsert(db, user, self.client_ip(), self.user_agent(), page_view=True)
            record_log(db, "page_view", "/", user, self.client_ip(), self.user_agent())
        self.send_json(HTTPStatus.OK, {"user": user})

    def handle_heartbeat(self):
        user = self.require_user()
        if not user:
            return
        self.send_json(HTTPStatus.OK, {"ok": True})

    def handle_track(self):
        user = self.require_user()
        if not user:
            return
        data = self.read_json()
        action = clean_text(data.get("action"), 40)
        path = clean_text(data.get("path"), 160)
        if action not in {"view_cat"}:
            raise ValueError("不支持的访问记录类型")
        with db_connect() as db:
            record_log(db, action, path, user, self.client_ip(), self.user_agent())
        self.send_json(HTTPStatus.OK, {"ok": True})

    def handle_list_cats(self):
        user = self.require_user()
        if not user:
            return
        with db_connect() as db:
            cats = list_cats(db)
        self.send_json(HTTPStatus.OK, {"cats": cats})

    def handle_list_notes(self):
        user = self.require_user()
        if not user:
            return
        with db_connect() as db:
            notes = list_notes(db)
        self.send_json(HTTPStatus.OK, {"notes": notes})

    def handle_create_note(self):
        user = self.require_user()
        if not user:
            return
        data = self.read_json()
        note = normalize_note(data)
        note_id = str(uuid.uuid4())
        created_at = iso_now()
        with db_connect() as db:
            db.execute(
                """
                INSERT INTO notes (
                    id, content, tone, author_student_id, author_name, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (note_id, note["content"], note["tone"], user["studentId"], user["name"], created_at),
            )
            row = db.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
            record_log(db, "create_note", note_id, user, self.client_ip(), self.user_agent())
        self.send_json(HTTPStatus.CREATED, {"note": note_from_row(row)})

    def handle_create_cat(self):
        user = self.require_admin()
        if not user:
            return
        data = self.read_json()
        normalized = normalize_cat(data)
        now = iso_now()
        cat = {
            **normalized,
            "id": str(uuid.uuid4()),
            "registryNo": "",
            "createdAt": now,
            "updatedAt": now,
        }
        with db_connect() as db:
            cat["registryNo"] = next_registry_no(db)
            cat_id = insert_cat(db, cat, user["studentId"], user["name"])
            row = db.execute("SELECT * FROM cats WHERE id = ?", (cat_id,)).fetchone()
            record_log(db, "create_cat", cat_id, user, self.client_ip(), self.user_agent())
        self.send_json(HTTPStatus.CREATED, {"cat": cat_from_row(row)})

    def handle_update_cat(self, cat_id):
        user = self.require_admin()
        if not user:
            return
        data = self.read_json()
        normalized = normalize_cat(data)
        now = iso_now()
        with db_connect() as db:
            existing = db.execute("SELECT * FROM cats WHERE id = ?", (cat_id,)).fetchone()
            if not existing:
                self.send_error_json(HTTPStatus.NOT_FOUND, "档案不存在")
                return
            db.execute(
                """
                UPDATE cats SET
                    photo_data = ?, name = ?, gender = ?, coat = ?, age = ?,
                    campus_area = ?, location = ?, status = ?, sterilized = ?,
                    vaccinated = ?, caretaker = ?, notes = ?, updated_at = ?,
                    updated_by_student_id = ?, updated_by_name = ?
                WHERE id = ?
                """,
                (
                    normalized["photoData"],
                    normalized["name"],
                    normalized["gender"],
                    normalized["coat"],
                    normalized["age"],
                    normalized["campusArea"],
                    normalized["location"],
                    normalized["status"],
                    normalized["sterilized"],
                    normalized["vaccinated"],
                    normalized["caretaker"],
                    normalized["notes"],
                    now,
                    user["studentId"],
                    user["name"],
                    cat_id,
                ),
            )
            row = db.execute("SELECT * FROM cats WHERE id = ?", (cat_id,)).fetchone()
            record_log(db, "update_cat", cat_id, user, self.client_ip(), self.user_agent())
        self.send_json(HTTPStatus.OK, {"cat": cat_from_row(row)})

    def handle_delete_cat(self, cat_id):
        user = self.require_admin()
        if not user:
            return
        with db_connect() as db:
            row = db.execute("SELECT name FROM cats WHERE id = ?", (cat_id,)).fetchone()
            if not row:
                self.send_error_json(HTTPStatus.NOT_FOUND, "档案不存在")
                return
            db.execute("DELETE FROM cats WHERE id = ?", (cat_id,))
            record_log(db, "delete_cat", f"{cat_id}:{row['name']}", user, self.client_ip(), self.user_agent())
        self.send_json(HTTPStatus.OK, {"ok": True})

    def handle_delete_note(self, note_id):
        user = self.require_user()
        if not user:
            return
        with db_connect() as db:
            row = db.execute(
                "SELECT id, author_student_id, author_name FROM notes WHERE id = ?",
                (note_id,),
            ).fetchone()
            if not row:
                self.send_error_json(HTTPStatus.NOT_FOUND, "便签不存在")
                return
            if user["role"] != "admin" and row["author_student_id"] != user["studentId"]:
                self.send_error_json(HTTPStatus.FORBIDDEN, "只能删除自己发布的便签")
                return
            db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            record_log(db, "delete_note", f"{note_id}:{row['author_name']}", user, self.client_ip(), self.user_agent())
        self.send_json(HTTPStatus.OK, {"ok": True})

    def handle_import(self):
        user = self.require_admin()
        if not user:
            return
        data = self.read_json()
        incoming = data.get("cats")
        if not isinstance(incoming, list):
            raise ValueError("导入文件中没有档案列表")
        if len(incoming) > 500:
            raise ValueError("一次最多导入 500 条档案")

        now = iso_now()
        with db_connect() as db:
            db.execute("DELETE FROM cats")
            for index, raw_cat in enumerate(incoming, start=1):
                if not isinstance(raw_cat, dict):
                    raise ValueError("导入档案格式不正确")
                normalized = normalize_cat(raw_cat)
                cat = {
                    **normalized,
                    "id": clean_text(raw_cat.get("id"), 80) or str(uuid.uuid4()),
                    "registryNo": f"WJIT-CAT-{index:03d}",
                    "createdAt": clean_text(raw_cat.get("createdAt"), 64) or now,
                    "updatedAt": now,
                }
                insert_cat(db, cat, user["studentId"], user["name"])
            record_log(db, "import_cats", str(len(incoming)), user, self.client_ip(), self.user_agent())
            cats = list_cats(db)
        self.send_json(HTTPStatus.OK, {"cats": cats})

    def handle_restore_samples(self):
        user = self.require_admin()
        if not user:
            return
        with db_connect() as db:
            db.execute("DELETE FROM cats")
            for cat in SAMPLE_CATS:
                insert_cat(db, cat, user["studentId"], user["name"])
            db.execute(
                "INSERT OR REPLACE INTO app_meta (key, value) VALUES ('sample_seeded', 'true')"
            )
            record_log(db, "restore_samples", str(len(SAMPLE_CATS)), user, self.client_ip(), self.user_agent())
            cats = list_cats(db)
        self.send_json(HTTPStatus.OK, {"cats": cats})

    def handle_admin_stats(self):
        user = self.require_admin()
        if not user:
            return
        today_local = datetime.now(CHINA_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        today_utc = iso_from_datetime(today_local)
        active_since = iso_from_datetime(utc_now() - timedelta(minutes=5))
        with db_connect() as db:
            metrics = {
                "totalViews": db.execute(
                    "SELECT COUNT(*) FROM access_logs WHERE action = 'page_view'"
                ).fetchone()[0],
                "todayViews": db.execute(
                    "SELECT COUNT(*) FROM access_logs WHERE action = 'page_view' AND created_at >= ?",
                    (today_utc,),
                ).fetchone()[0],
                "uniqueVisitors": db.execute("SELECT COUNT(*) FROM visitors").fetchone()[0],
                "activeVisitors": db.execute(
                    "SELECT COUNT(*) FROM visitors WHERE last_seen >= ?", (active_since,)
                ).fetchone()[0],
                "loginCount": db.execute(
                    "SELECT COUNT(*) FROM access_logs WHERE action = 'login'"
                ).fetchone()[0],
                "catCount": db.execute("SELECT COUNT(*) FROM cats").fetchone()[0],
            }
            visitor_rows = db.execute(
                """
                SELECT student_id, name, role, first_seen, last_seen, login_count,
                       page_views, last_ip, last_user_agent
                FROM visitors
                ORDER BY last_seen DESC
                LIMIT 300
                """
            ).fetchall()
            log_rows = db.execute(
                """
                SELECT student_id, name, role, action, path, ip, user_agent, created_at
                FROM access_logs
                ORDER BY id DESC
                LIMIT 300
                """
            ).fetchall()

        visitors = [
            {
                "studentId": row["student_id"],
                "name": row["name"],
                "role": row["role"],
                "firstSeen": row["first_seen"],
                "lastSeen": row["last_seen"],
                "loginCount": row["login_count"],
                "pageViews": row["page_views"],
                "lastIp": row["last_ip"],
                "lastUserAgent": row["last_user_agent"],
            }
            for row in visitor_rows
        ]
        logs = [
            {
                "studentId": row["student_id"],
                "name": row["name"],
                "role": row["role"],
                "action": row["action"],
                "path": row["path"],
                "ip": row["ip"],
                "userAgent": row["user_agent"],
                "createdAt": row["created_at"],
            }
            for row in log_rows
        ]
        self.send_json(HTTPStatus.OK, {"metrics": metrics, "visitors": visitors, "logs": logs})

    def serve_static(self, request_path):
        if request_path in {"/", "/index.html"}:
            relative = Path("index.html")
            with db_connect() as db:
                record_log(db, "landing", request_path, None, self.client_ip(), self.user_agent())
        elif request_path in {"/styles.css", "/app.js"}:
            relative = Path(request_path.lstrip("/"))
        elif request_path.startswith("/assets/"):
            relative = Path(unquote(request_path.lstrip("/")))
        else:
            self.send_error_json(HTTPStatus.NOT_FOUND, "页面不存在")
            return

        target = (BASE_DIR / relative).resolve()
        if target != BASE_DIR and BASE_DIR not in target.parents:
            self.send_error_json(HTTPStatus.FORBIDDEN, "禁止访问")
            return
        if not target.is_file():
            self.send_error_json(HTTPStatus.NOT_FOUND, "文件不存在")
            return

        content = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if target.suffix in {".html", ".css", ".js"}:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "public, max-age=86400" if request_path.startswith("/assets/") else "no-cache")
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), RegistryHandler)
    print(f"Wanjiang cat registry running on http://{HOST}:{PORT}")
    print(f"Admin identity: {ADMIN_STUDENT_ID} / {ADMIN_NAME}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
