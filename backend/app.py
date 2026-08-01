from datetime import datetime
from pathlib import Path
from typing import Optional
import hashlib
import hmac
import os
import secrets
import shutil
import uuid

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from database import Complaint, Notification, SessionLocal, User
from detector import detect_damage
from issue_catalog import ISSUE_CATALOG, ISSUES_BY_KEY


app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
ALLOWED_STATUSES = {"Pending", "In Progress", "Completed"}
DEFAULT_ADMIN_USERNAME = os.getenv("NEUROSCAN_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("NEUROSCAN_ADMIN_PASSWORD", "Admin@123")
COMPLETION_REWARD_POINTS = 50
PRIORITY_REDEEM_COST = 50

os.makedirs(BASE_DIR / "uploads", exist_ok=True)
os.makedirs(BASE_DIR / "outputs", exist_ok=True)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("NEUROSCAN_SESSION_SECRET", "neuroscan_secret_key"),
    same_site="lax",
    max_age=60 * 60 * 8,
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/outputs", StaticFiles(directory=BASE_DIR / "outputs"), name="outputs")
app.mount("/uploads", StaticFiles(directory=BASE_DIR / "uploads"), name="uploads")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def normalize_mobile(mobile: str) -> str:
    digits_only = "".join(ch for ch in mobile if ch.isdigit())
    if len(digits_only) == 10:
        return digits_only
    if len(digits_only) == 12 and digits_only.startswith("91"):
        return digits_only[-10:]
    return digits_only


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_value.encode("utf-8"),
        120000,
    ).hex()
    return f"pbkdf2_sha256$120000${salt_value}${digest}"


def verify_password(password: str, stored_value: Optional[str]) -> bool:
    if not stored_value:
        return False

    if stored_value.startswith("pbkdf2_sha256$"):
        _, iterations, salt, digest = stored_value.split("$", 3)
        computed_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(computed_digest, digest)

    return hmac.compare_digest(password, stored_value)


def get_current_user_session(request: Request) -> Optional[dict]:
    user_session = request.session.get("user")
    if isinstance(user_session, dict) and user_session.get("role") == "user":
        return user_session
    return None


def get_current_admin_session(request: Request) -> Optional[dict]:
    admin_session = request.session.get("admin")
    if isinstance(admin_session, dict) and admin_session.get("role") == "admin":
        return admin_session
    return None


def build_image_url(image_path: Optional[str]) -> str:
    if not image_path:
        return ""

    image_file = Path(image_path)
    parent_name = image_file.parent.name
    if parent_name == "uploads":
        return f"/uploads/{image_file.name}"
    return f"/outputs/{image_file.name}"


def format_timestamp() -> str:
    return datetime.now().strftime("%d %b %Y, %I:%M %p")


def parse_truthy(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def unread_notification_count(user_id: Optional[int]) -> int:
    if not user_id:
        return 0

    db = SessionLocal()
    try:
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        ).count()
    finally:
        db.close()


def create_notification(db, user: Optional[User], complaint: Complaint, title: str, message: str, status_snapshot: str) -> None:
    if not user:
        return

    channel = "SMS Ready" if getattr(user, "sms_opt_in", 1) else "In-App"
    notification = Notification(
        user_id=user.id,
        complaint_id=complaint.id,
        title=title,
        message=message,
        channel=channel,
        status_snapshot=status_snapshot,
        created_at=format_timestamp(),
        read_at=None,
    )
    db.add(notification)


def portal_context(request: Request) -> dict:
    current_user = get_current_user_session(request)
    current_admin = get_current_admin_session(request)
    return {
        "request": request,
        "user": current_user,
        "admin": current_admin,
        "unread_notifications": unread_notification_count(current_user.get("id")) if current_user else 0,
    }


def grouped_issue_catalog():
    groups = {}
    for issue in ISSUE_CATALOG:
        groups.setdefault(issue["group"], []).append(issue)
    return groups


def build_analysis_result(issue: dict, upload_path: Path):
    detection_mode = issue["detection_mode"]

    if detection_mode == "ai" and issue.get("model_key"):
        detections, confidence, output_path, severity = detect_damage(str(upload_path), issue["model_key"])
        review_note = (
            "AI image review completed. The report is queued with model-assisted evidence for admin verification."
            if detections
            else "No strong object match was found. The image is still queued for admin review."
        )
        return {
            "detections": detections,
            "confidence": confidence,
            "output_path": output_path or str(upload_path),
            "detection_mode": "AI Assisted",
            "model_key": issue["model_key"],
            "severity": severity,
            "review_note": review_note,
        }

    return {
        "detections": [],
        "confidence": 0,
        "output_path": str(upload_path),
        "detection_mode": "Manual Review",
        "model_key": None,
        "severity": "Needs Review",
        "review_note": "This category is routed to admin review directly because it needs context, human judgment, or non-image data.",
    }


def seed_admin_account() -> None:
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == "admin", User.username == DEFAULT_ADMIN_USERNAME).first()

        if not admin:
            admin = User(
                username=DEFAULT_ADMIN_USERNAME,
                password=hash_password(DEFAULT_ADMIN_PASSWORD),
                role="admin",
                full_name="NeuroScan Administrator",
                contact_number="0000000000",
            )
            db.add(admin)
            db.commit()
            return

        if not str(admin.password or "").startswith("pbkdf2_sha256$"):
            admin.password = hash_password(DEFAULT_ADMIN_PASSWORD)
            db.commit()
    finally:
        db.close()


seed_admin_account()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html", portal_context(request))


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, tab: str = "user"):
    if get_current_admin_session(request):
        return RedirectResponse("/admin/dashboard", status_code=302)

    if get_current_user_session(request):
        return RedirectResponse("/report", status_code=302)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request,
            "error": None,
            "success": None,
            "active_tab": tab if tab in {"user", "admin"} else "user",
        },
    )


@app.post("/register/user")
async def register_user(
    request: Request,
    full_name: str = Form(...),
    mobile: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    normalized_mobile = normalize_mobile(mobile)

    if len(full_name.strip()) < 3:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "error": "Enter a valid full name.",
                "success": None,
                "active_tab": "user",
            },
            status_code=400,
        )

    if len(normalized_mobile) != 10:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "error": "Use a valid 10-digit mobile number.",
                "success": None,
                "active_tab": "user",
            },
            status_code=400,
        )

    if len(password) < 8:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "error": "Password must be at least 8 characters long.",
                "success": None,
                "active_tab": "user",
            },
            status_code=400,
        )

    if password != confirm_password:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "error": "Passwords do not match.",
                "success": None,
                "active_tab": "user",
            },
            status_code=400,
        )

    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.contact_number == normalized_mobile).first()
        if existing_user:
            return templates.TemplateResponse(
                request,
                "login.html",
                {
                    "request": request,
                    "error": "An account with this mobile number already exists.",
                    "success": None,
                    "active_tab": "user",
                },
                status_code=409,
            )

        username_base = normalized_mobile
        username = username_base
        counter = 1
        while db.query(User).filter(User.username == username).first():
            counter += 1
            username = f"{username_base}_{counter}"

        user = User(
            username=username,
            password=hash_password(password),
            role="user",
            full_name=full_name.strip(),
            contact_number=normalized_mobile,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request,
            "error": None,
            "success": "Account created. Sign in with your mobile number and password.",
            "active_tab": "user",
        },
    )


@app.post("/login/user")
async def user_login(
    request: Request,
    mobile: str = Form(...),
    password: str = Form(...),
):
    normalized_mobile = normalize_mobile(mobile)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.contact_number == normalized_mobile, User.role == "user").first()
    finally:
        db.close()

    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "error": "Invalid mobile number or password.",
                "success": None,
                "active_tab": "user",
            },
            status_code=401,
        )

    request.session.clear()
    request.session["user"] = {
        "id": user.id,
        "name": user.full_name or "Citizen",
        "mobile": user.contact_number,
        "role": "user",
    }
    return RedirectResponse("/report", status_code=302)


@app.post("/login/admin")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == username.strip(), User.role == "admin").first()
    finally:
        db.close()

    if not admin or not verify_password(password, admin.password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "error": "Invalid administrator credentials.",
                "success": None,
                "active_tab": "admin",
            },
            status_code=401,
        )

    request.session.clear()
    request.session["admin"] = {
        "id": admin.id,
        "name": admin.full_name or admin.username,
        "username": admin.username,
        "role": "admin",
    }
    return RedirectResponse("/admin/dashboard", status_code=302)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


@app.get("/admin")
async def admin_redirect(request: Request):
    if not get_current_admin_session(request):
        return RedirectResponse("/login?tab=admin", status_code=302)
    return RedirectResponse("/admin/dashboard", status_code=302)


@app.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login?tab=admin", status_code=302)


@app.get("/report", response_class=HTMLResponse)
async def report_page(request: Request):
    current_user = get_current_user_session(request)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    db = SessionLocal()
    try:
        user_record = db.query(User).filter(User.id == current_user.get("id")).first()
        available_credits = getattr(user_record, "credit_points", 0) if user_record else 0
    finally:
        db.close()

    return templates.TemplateResponse(
        request,
        "report.html",
        {
            **portal_context(request),
            "issue_groups": grouped_issue_catalog(),
            "issue_catalog": ISSUE_CATALOG,
            "available_credits": available_credits,
            "priority_redeem_cost": PRIORITY_REDEEM_COST,
        },
    )


@app.get("/my-reports", response_class=HTMLResponse)
async def my_reports(request: Request):
    current_user = get_current_user_session(request)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    db = SessionLocal()
    available_credits = 0
    total_earned_credits = 0
    try:
        user_record = db.query(User).filter(User.id == current_user.get("id")).first()
        if user_record:
            available_credits = int(getattr(user_record, "credit_points", 0) or 0)
            total_earned_credits = int(getattr(user_record, "total_points_earned", 0) or 0)
        notifications = db.query(Notification).filter(
            Notification.user_id == current_user.get("id")
        ).order_by(Notification.id.desc()).limit(20).all()

        current_time = format_timestamp()
        for notification in notifications:
            if notification.read_at is None:
                notification.read_at = current_time
        db.commit()

        complaints = db.query(Complaint).filter(
            Complaint.user_id == current_user.get("id")
        ).order_by(Complaint.id.desc()).all()
        notifications = db.query(Notification).filter(
            Notification.user_id == current_user.get("id")
        ).order_by(Notification.id.desc()).limit(20).all()

        for complaint in complaints:
            complaint.image_url = build_image_url(complaint.image_path)
    finally:
        db.close()

    report_stats = {
        "total": len(complaints),
        "pending": sum(1 for complaint in complaints if complaint.status == "Pending"),
        "in_progress": sum(1 for complaint in complaints if complaint.status == "In Progress"),
        "completed": sum(1 for complaint in complaints if complaint.status == "Completed"),
    }
    credit_summary = {
        "available": available_credits,
        "earned": total_earned_credits,
        "priority_used": sum(1 for complaint in complaints if getattr(complaint, "priority_requested", 0)),
    }

    return templates.TemplateResponse(
        request,
        "my_reports.html",
        {
            **portal_context(request),
            "complaints": complaints,
            "notifications": notifications,
            "report_stats": report_stats,
            "credit_summary": credit_summary,
            "completion_reward_points": COMPLETION_REWARD_POINTS,
            "priority_redeem_cost": PRIORITY_REDEEM_COST,
        },
    )


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    admin_session = get_current_admin_session(request)
    if not admin_session:
        return RedirectResponse("/login?tab=admin", status_code=302)

    db = SessionLocal()
    try:
        complaints = db.query(Complaint).order_by(Complaint.id.desc()).all()
    finally:
        db.close()

    stats = {
        "total": len(complaints),
        "pending": sum(1 for complaint in complaints if complaint.status == "Pending"),
        "in_progress": sum(1 for complaint in complaints if complaint.status == "In Progress"),
        "completed": sum(1 for complaint in complaints if complaint.status == "Completed"),
        "priority": sum(1 for complaint in complaints if getattr(complaint, "priority_requested", 0)),
    }

    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "request": request,
            "complaints": complaints,
            "stats": stats,
            "admin": admin_session,
            "status_choices": ["Pending", "In Progress", "Completed"],
            "completion_reward_points": COMPLETION_REWARD_POINTS,
        },
    )


@app.get("/admin/report/{report_id}", response_class=HTMLResponse)
async def report_detail(request: Request, report_id: int):
    admin_session = get_current_admin_session(request)
    if not admin_session:
        return RedirectResponse("/login?tab=admin", status_code=302)

    db = SessionLocal()
    try:
        report = db.query(Complaint).filter(Complaint.id == report_id).first()
    finally:
        db.close()

    if not report:
        return HTMLResponse("Report not found", status_code=404)

    return templates.TemplateResponse(
        request,
        "report_detail.html",
        {
            "request": request,
            "report": report,
            "image_url": build_image_url(report.image_path),
            "status_choices": sorted(ALLOWED_STATUSES, key=lambda value: ["Pending", "In Progress", "Completed"].index(value)),
            "image_analysis_mode": report.detection_mode or "Manual Review",
            "completion_reward_points": COMPLETION_REWARD_POINTS,
        },
    )


@app.get("/admin/download/{report_id}")
async def download_report(request: Request, report_id: int):
    if not get_current_admin_session(request):
        return RedirectResponse("/login?tab=admin", status_code=302)

    db = SessionLocal()
    try:
        report = db.query(Complaint).filter(Complaint.id == report_id).first()
    finally:
        db.close()

    if not report or not report.image_path:
        return JSONResponse({"error": "Report not found"}, status_code=404)

    return FileResponse(path=report.image_path, filename=f"report_{report_id}.jpg")


@app.post("/admin/update/{complaint_id}")
async def update_status(request: Request, complaint_id: int):
    if not get_current_admin_session(request):
        return JSONResponse({"success": False, "error": "Unauthorized"}, status_code=401)

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
        status = str(payload.get("status", "")).strip()
    else:
        form = await request.form()
        status = str(form.get("status", "")).strip()

    if status not in ALLOWED_STATUSES:
        return JSONResponse({"success": False, "error": "Invalid status"}, status_code=400)

    db = SessionLocal()
    updated_at = format_timestamp()
    try:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            return JSONResponse({"success": False, "error": "Complaint not found"}, status_code=404)

        previous_status = complaint.status or "Pending"
        complaint.status = status
        complaint.last_updated_at = updated_at

        user = None
        if complaint.user_id:
            user = db.query(User).filter(User.id == complaint.user_id).first()

        reward_granted_now = False
        if status == "Completed" and previous_status != "Completed" and user and not getattr(complaint, "reward_points", 0):
            user.credit_points = int(getattr(user, "credit_points", 0) or 0) + COMPLETION_REWARD_POINTS
            user.total_points_earned = int(getattr(user, "total_points_earned", 0) or 0) + COMPLETION_REWARD_POINTS
            complaint.reward_points = COMPLETION_REWARD_POINTS
            reward_granted_now = True

        if status != previous_status:
            notification_message = f"Your {complaint.issue_type} report is now marked as {status}."
            if reward_granted_now:
                notification_message += f" {COMPLETION_REWARD_POINTS} credits have been added to your wallet."
            create_notification(
                db,
                user,
                complaint,
                title=f"Report {complaint.reference_code or complaint.id} updated",
                message=notification_message,
                status_snapshot=status,
            )
        db.commit()
    finally:
        db.close()

    return JSONResponse(
        {
            "success": True,
            "status": status,
            "updated_at": updated_at,
            "reward_granted": reward_granted_now,
            "reward_points": COMPLETION_REWARD_POINTS if reward_granted_now else 0,
        }
    )


@app.get("/success", response_class=HTMLResponse)
async def success_page(
    request: Request,
    id: str,
    type: str,
    img: str,
    conf: float,
    lat: float,
    lon: float,
    msg: str = "",
    mode: str = "AI Assisted",
    note: str = "",
    severity: str = "Needs Review",
):
    return templates.TemplateResponse(
        request,
        "success.html",
        {
            "request": request,
            "report_id": id,
            "issue_type": type.title(),
            "image_url": img,
            "confidence": int(float(conf) * 100),
            "latitude": lat,
            "longitude": lon,
            "comment": msg,
            "analysis_mode": mode,
            "analysis_note": note,
            "severity": severity,
        },
    )


@app.post("/detect")
async def detect(
    request: Request,
    file: UploadFile = File(...),
    issue_type: str = Form(...),
    comment: str = Form(""),
    latitude: float = Form(...),
    longitude: float = Form(...),
    use_credits: str = Form("false"),
):
    current_user = get_current_user_session(request)
    if not current_user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    issue = ISSUES_BY_KEY.get(issue_type)
    if not issue:
        return JSONResponse({"error": "Unsupported issue category"}, status_code=400)

    unique_id = uuid.uuid4()
    filename = f"{unique_id}_{Path(file.filename or 'report.jpg').name}"
    upload_path = BASE_DIR / "uploads" / filename

    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    analysis = build_analysis_result(issue, upload_path)

    reference_code = f"CE-{unique_id.hex[:8].upper()}"
    created_at = format_timestamp()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == current_user.get("id")).first()
        wants_priority = parse_truthy(use_credits)
        if wants_priority:
            if not user:
                return JSONResponse({"error": "User account not found."}, status_code=404)
            current_credits = int(getattr(user, "credit_points", 0) or 0)
            if current_credits < PRIORITY_REDEEM_COST:
                return JSONResponse(
                    {"error": f"You need at least {PRIORITY_REDEEM_COST} credits to use priority handling."},
                    status_code=400,
                )
            user.credit_points = current_credits - PRIORITY_REDEEM_COST

        complaint = Complaint(
            reference_code=reference_code,
            issue_key=issue["key"],
            issue_type=issue["label"],
            image_path=str(analysis["output_path"]),
            confidence=analysis["confidence"],
            latitude=latitude,
            longitude=longitude,
            comment=comment.strip(),
            status="Pending",
            user_name=current_user.get("name"),
            user_contact=current_user.get("mobile"),
            created_at=created_at,
            user_id=current_user.get("id"),
            detection_mode=analysis["detection_mode"],
            model_key=analysis["model_key"],
            severity=analysis["severity"],
            last_updated_at=created_at,
            priority_requested=1 if wants_priority else 0,
        )
        db.add(complaint)
        db.flush()

        create_notification(
            db,
            user,
            complaint,
            title=f"Report {reference_code} submitted",
            message=(
                f"Your {issue['label']} complaint has been logged and is currently Pending."
                + (f" {PRIORITY_REDEEM_COST} credits were used for priority handling." if wants_priority else "")
            ),
            status_snapshot="Pending",
        )
        db.commit()
    finally:
        db.close()

    return JSONResponse(
        {
            "report_id": reference_code,
            "confidence": analysis["confidence"],
            "image_url": build_image_url(analysis["output_path"]),
            "detections": analysis["detections"],
            "analysis_mode": analysis["detection_mode"],
            "review_note": analysis["review_note"],
            "severity": analysis["severity"],
            "issue_label": issue["label"],
            "priority_requested": wants_priority,
        }
    )
