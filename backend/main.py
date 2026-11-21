import html
import logging
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from backend.schemas.contracts import ProjectRequest, ApprovalRequest, AnswersRequest
from backend.storage import save_project, load_project, project_dir, list_project_ids
from backend import artifacts, security
from backend.agents.architect import ArchitectureError, build_architecture
from backend.agents.business_analyst.analyst import analyze
from backend.agents.business_analyst.config import ConfigError, get_settings as get_ba_settings
from backend.agents.business_analyst.errors import describe_failure
from backend.agents.business_analyst.revision import summarize_revision
from backend.orchestrator import run_pipeline

logger = logging.getLogger("uvicorn.error").getChild("bunyan.analysis")

# Workflow status for each Business Analyst verdict.
STATUS_FOR_VERDICT = {
    "ready_for_review": "awaiting_approval",
    "needs_clarification": "awaiting_clarification",
    "rejected_out_of_scope": "rejected",
}

# Statuses in which the generation pipeline is working on a project.
PIPELINE_STATES = ("designing", "developing", "testing", "documenting")

# Sent with every generated file. The generated app is untrusted code served
# from the backend's own origin, so the preview may only load its own files:
# no inline scripts, no requests to this API or to any other host.
# "sandbox" gives the preview an opaque origin even when opened in its own tab: it
# cannot read this site's storage or cookies, script the page around it, or call the
# API as the logged-in user. The app then keeps its records in memory.
PREVIEW_HEADERS = {
    "Content-Security-Policy": (
        "sandbox allow-scripts allow-forms allow-modals; "
        "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "base-uri 'none'; form-action 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
}

def preview_headers(request):
    """PREVIEW_HEADERS with this server's origin written out instead of 'self'.

    In a sandboxed (opaque-origin) document, browsers differ on what 'self' matches;
    the explicit origin lets the app load its own style.css and app.js everywhere.
    """
    origin = f"{request.url.scheme}://{request.url.netloc}"
    headers = dict(PREVIEW_HEADERS)
    headers["Content-Security-Policy"] = headers["Content-Security-Policy"].replace("'self'", origin)
    return headers


# Makes "check the status, then start the pipeline" one step, so two approvals
# sent at the same moment cannot both start a run.
_approval_lock = threading.Lock()
_running_lock = threading.Lock()
_running_projects = set()


def check_ba_configuration():
    """Validate the Business Analyst settings once at startup.

    BA_MODE=mock (default) or llm. A value the agent does not accept (BA_MODE,
    BA_LLM_BACKEND, BA_EFFORT, ...) stops the server with a ConfigError that names it.
    LLM mode without a model or key is logged here; each analysis then fails with
    "ba_not_configured". There is never a silent fallback to mock.
    """
    settings = get_ba_settings()
    if settings.mode == "llm":
        try:
            settings.check_llm_ready()
        except ConfigError as exc:
            logger.error("Business Analyst: BA_MODE=llm but the LLM is not configured: %s", exc)
        else:
            logger.info("Business Analyst: LLM mode (provider %s, model %s, backend %s)",
                        settings.provider, settings.model, settings.backend)
    else:
        logger.info("Business Analyst: mock mode (BA_MODE=mock); set BA_MODE=llm for real analysis")
    return settings


@asynccontextmanager
async def lifespan(app):
    security.check_configuration()
    check_ba_configuration()
    recover_interrupted_projects()
    yield


app = FastAPI(title="Bunyan AI Backend", lifespan=lifespan)

# Which web pages may call this API from the browser. By default only a frontend
# served from this machine (any port), so another website open in the same
# browser cannot read or create projects. For a deployed frontend, set
# BUNYAN_CORS_ORIGINS to a comma-separated list of its origins.
LOCAL_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
CORS_ORIGINS = [o.strip() for o in os.environ.get("BUNYAN_CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=LOCAL_ORIGIN_REGEX,
    allow_credentials=False,  # the frontend sends no cookies or credentials
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def access_control(request: Request, call_next):
    """Server-side access control for every route except the health check.

    With BUNYAN_AUTH=required the request needs valid Basic credentials; the user name
    is kept on request.state for the ownership checks. CORS is not authentication.
    """
    request.state.user = None
    client = request.client.host if request.client else "unknown"
    request.state.client = client
    new_cookie = None
    mode = security.auth_mode()
    if request.url.path != "/health" and mode != "off":
        try:
            if mode == "required":
                request.state.user = await run_in_threadpool(
                    security.authenticator.authenticate, request.headers.get("authorization"), client
                )
            else:  # guest: an anonymous identity from a signed cookie, issued on the first visit
                if request.method not in ("GET", "HEAD", "OPTIONS") and not same_origin(request):
                    raise HTTPException(403, "Requests from other sites are not accepted.")
                request.state.user, new_cookie = security.guest_sessions.identify(
                    request.cookies.get(security.GUEST_COOKIE), client, needed=is_api_path(request.url.path)
                )
        except HTTPException as exc:
            return error_response(request, exc)
    response = await call_next(request)
    if response.headers.get("content-type") == "application/json":
        response.headers["content-type"] = "application/json; charset=utf-8"  # Safari guesses otherwise
    if new_cookie:
        response.set_cookie(
            security.GUEST_COOKIE, new_cookie, max_age=security.GUEST_SESSION_SECONDS, path="/",
            httponly=True, samesite="lax",
            secure=os.environ.get("BUNYAN_COOKIE_SECURE", "true").strip().lower() != "false",
        )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


def is_api_path(path: str) -> bool:
    """Routes that read or change a guest's projects. Everything else is the public React app."""
    return path == "/projects" or path.startswith("/projects/")


_ERROR_TITLES = {401: "تسجيل الدخول مطلوب", 403: "الطلب مرفوض", 404: "الصفحة غير موجودة",
                 429: "طلبات كثيرة"}


def wants_html(request: Request) -> bool:
    """A browser opening a page (address bar, link), not the app's own fetch() calls."""
    return request.method in ("GET", "HEAD") and "text/html" in request.headers.get("accept", "")


def error_response(request: Request, exc: HTTPException) -> Response:
    """JSON (UTF-8) for the app's API calls; a small Arabic page when a person opens a URL."""
    if not wants_html(request):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers,
                            media_type="application/json; charset=utf-8")
    title = _ERROR_TITLES.get(exc.status_code, "حدث خطأ")
    detail = html.escape(str(exc.detail))
    page = f"""<!doctype html>
<html lang="ar" dir="rtl" data-theme="light"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#F8F7FC">
<title>بُنيان: {title}</title>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;600;700&display=swap">
<script>/* the same theme choice as the app (bunyan.prefs, light by default) */
try{{var t=(JSON.parse(localStorage.getItem('bunyan.prefs'))||{{}}).theme||'light';
if(t==='system')document.documentElement.removeAttribute('data-theme');else document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>
<style>
:root{{--bn-bg:#ffffff;--bn-bg-subtle:#f8f7fc;--bn-border:#e6e2f2;--bn-text:#17123a;--bn-text-2:#3b3560;
--bn-accent:#5b3fa8;--bn-accent-hover:#4a3290;--bn-on-accent:#ffffff;
--bn-shadow:0 12px 32px rgb(23 18 58 / .14),0 2px 6px rgb(23 18 58 / .06);
--bn-font:'IBM Plex Sans Arabic','IBM Plex Sans','Segoe UI',Tahoma,sans-serif;color-scheme:light}}
@media (prefers-color-scheme:dark){{:root:not([data-theme='light']){{--bn-bg:#0b0d1f;--bn-bg-subtle:#121634;--bn-border:#262a4d;
--bn-text:#f4f2fa;--bn-text-2:#c8c4da;--bn-accent:#c9bff2;--bn-accent-hover:#ddd6fb;--bn-on-accent:#17123a;
--bn-shadow:0 12px 32px rgb(0 0 0 / .5),0 0 0 1px #262a4d;color-scheme:dark}}}}
:root[data-theme='dark']{{--bn-bg:#0b0d1f;--bn-bg-subtle:#121634;--bn-border:#262a4d;--bn-text:#f4f2fa;--bn-text-2:#c8c4da;
--bn-accent:#c9bff2;--bn-accent-hover:#ddd6fb;--bn-on-accent:#17123a;--bn-shadow:0 12px 32px rgb(0 0 0 / .5),0 0 0 1px #262a4d;color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;min-height:100vh;display:grid;place-items:center;padding:16px;background:var(--bn-bg-subtle);
color:var(--bn-text);font-family:var(--bn-font);line-height:1.7}}
main{{background:var(--bn-bg);border:1px solid var(--bn-border);border-radius:12px;box-shadow:var(--bn-shadow);
max-width:460px;width:100%;padding:32px 28px;text-align:center}}
.brand{{display:inline-flex;align-items:center;gap:8px;font-weight:700;margin-bottom:20px;color:var(--bn-text)}}
.brand img{{width:24px;height:24px}}
h1{{font-size:1.375rem;font-weight:700;margin:0 0 8px}}
p{{color:var(--bn-text-2);margin:0 0 24px}}
a.btn{{display:inline-block;background:var(--bn-accent);color:var(--bn-on-accent);text-decoration:none;font-weight:600;
padding:10px 24px;border-radius:8px}}
a.btn:hover{{background:var(--bn-accent-hover)}}
a.btn:focus-visible{{outline:3px solid var(--bn-accent);outline-offset:3px}}
</style></head>
<body><main><div class="brand"><img src="/favicon.svg" alt="">بُنيان</div>
<h1>{title}</h1><p>{detail}</p><a class="btn" href="/">العودة إلى بُنيان</a></main></body></html>"""
    headers = {k: v for k, v in (exc.headers or {}).items() if k.lower() != "www-authenticate"} \
        if exc.status_code != 401 else (exc.headers or {})
    return Response(page, status_code=exc.status_code, headers=headers, media_type="text/html; charset=utf-8")


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    """Route errors (e.g. a preview link that is not yours, 404) the same way as the middleware's."""
    return error_response(request, exc)


def same_origin(request):
    """A browser sends Origin with cross-site writes; it must be this site (SameSite=Lax also blocks them)."""
    origin = request.headers.get("origin")
    return origin is None or origin == f"{request.url.scheme}://{request.url.netloc}"


def current_user(request: Request):
    return getattr(request.state, "user", None)


def current_client(request: Request):
    return getattr(request.state, "client", "unknown")


def enforce_limits(user, new_project=False, analysis=False, client="unknown"):
    """Rate and quota checks for a shared deployment. Returns True when an LLM slot was taken."""
    if not security.shared_deployment():
        return False
    security.limits.check_rate(user, client)
    if not analysis:
        return False
    try:
        llm = get_ba_settings().mode == "llm"
    except ConfigError:
        llm = False  # the analysis will fail with "ba_not_configured" without calling a model
    if llm and security.auth_mode() == "guest":
        raise HTTPException(403, "Real analysis is not available to guests.")  # startup refuses this too
    security.limits.reserve(user, new_project=new_project, llm=llm, client=client)
    return llm


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def save_with_timestamp(project):
    project["updated_at"] = now_iso()
    save_project(project)


def get_existing_project(project_id, user=None):
    """The project, or 404 when it does not exist or belongs to another user."""
    project = load_project(str(project_id))
    if project is None or not security.can_access(project, user):
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def run_generation(project_id):
    """Background task: Architect -> Developer for one approved project.

    Runs after the approve response has been sent. Every state change is saved
    through save_with_timestamp. Whatever goes wrong, the project ends in
    "completed" or "failed", never stuck in a working status.
    """
    project_id = str(project_id)
    with _running_lock:
        if project_id in _running_projects:
            return
        _running_projects.add(project_id)
    try:
        project = load_project(project_id)
        # Only a project that approve_project just moved to "designing" is run.
        # This also keeps a finished project's files from being generated again.
        if (
            project is None
            or project.get("status") != "designing"
            or project.get("requirements_approved") is not True
        ):
            return
        try:
            run_pipeline(project, project_dir(project_id), save_with_timestamp)
        except Exception as exc:
            project["status"] = "failed"
            project["error"] = {
                "code": "pipeline_failed",
                "message": f"Generation stopped unexpectedly: {type(exc).__name__}: {exc}",
            }
            try:
                save_with_timestamp(project)
            except Exception:
                pass  # storage itself is failing; recover_interrupted_projects handles it on restart
    finally:
        with _running_lock:
            _running_projects.discard(project_id)


def recover_interrupted_projects():
    """Mark runs that were cut off by a server restart as failed.

    Background tasks do not survive a restart, so a project still in a working
    status at startup would otherwise stay there forever.
    """
    recovered = []
    for project_id in list_project_ids():
        project = load_project(project_id)
        if project and project.get("status") == "analyzing":
            analysis_interrupted(project)
            recovered.append(project_id)
        elif project and project.get("status") in PIPELINE_STATES:
            project["status"] = "failed"
            project["error"] = {
                "code": "pipeline_interrupted",
                "message": "The server restarted while the application was being generated",
            }
            save_with_timestamp(project)
            recovered.append(project_id)
    return recovered


def analysis_interrupted(project):
    """A restart cut off an analysis: keep the reviewed version if there is one."""
    previous_status = (project.get("analysis") or {}).get("previous_status")
    project["status"] = previous_status if previous_status and project.get("requirements") else "failed"
    project["error"] = {
        "code": "analysis_interrupted",
        "message": "توقف الخادم أثناء تحليل الفكرة. أعد إرسال طلبك.",
        "retryable": True,
    }
    save_with_timestamp(project)


def requirements_compatibility(requirements):
    """Can the Architect build these requirements? Checked before the user approves them.

    Only for documents ready for review. A refusal (for example two entities or a
    reference field) is reported, not blocked: approval still works as before and
    the run stops at the Architect, so the warning lets the user ask for a change first.
    """
    if not requirements or requirements.get("status") != "ready_for_review":
        return None
    try:
        build_architecture(requirements)
    except ArchitectureError as exc:
        return {
            "supported": False,
            "message": "هذه النسخة من بُنيان تبني نوع سجل واحد بلا روابط بين السجلات. "
                       "اطلب تعديلاً لتبسيط المتطلبات قبل الموافقة، وإلا سيتوقف البناء عند مهندس البرمجيات.",
            "reasons": list(exc.reasons),
        }
    except Exception as exc:  # noqa: BLE001 - an Architect crash must not block the analysis, but must be visible
        logger.warning("Architect check crashed on requirements under review: %s: %s", type(exc).__name__, str(exc)[:300])
        return {
            "supported": False,
            "message": "تعذّر على مهندس البرمجيات فحص هذه المتطلبات بسبب خطأ داخلي، فقد يتوقف البناء عنده. "
                       "اطلب تعديلاً بسيطاً أو أبلغ فريق بُنيان.",
            "reasons": [f"architect_check_failed: {type(exc).__name__}"],
        }
    return {"supported": True, "message": None, "reasons": []}


def start_analysis(project, background_tasks, kind, answers=None, feedback=None, llm_slot=False):
    """Run the Business Analyst for a new idea ("initial"), answers or feedback.

    Mock mode (BA_MODE=mock, the default) answers within the request, as before.
    LLM mode (BA_MODE=llm) can take minutes, longer than the frontend's request
    timeout, so the request returns at once with status "analyzing" and the
    analysis runs in the background; the frontend already polls that status.
    """
    try:
        settings = get_ba_settings()
    except ConfigError:
        settings = None  # finish_analysis reports it as "ba_not_configured"
    # The endpoints have checked this status (awaiting_approval for feedback,
    # awaiting_clarification for answers); a failed re-analysis returns to it.
    previous_status = None if kind == "initial" else project["status"]
    project["status"] = "analyzing"
    project["current_agent"] = "business_analyst"
    project["error"] = None
    project["analysis"] = {
        "mode": settings.mode if settings else None,
        "kind": kind,
        "previous_status": previous_status,
        "started_at": now_iso(),
    }
    save_with_timestamp(project)
    if settings is not None and settings.mode == "llm":
        background_tasks.add_task(run_analysis_in_background, project["project_id"], answers, feedback, llm_slot)
        return project
    try:
        return finish_analysis(project, answers=answers, feedback=feedback, settings=settings)
    finally:
        if llm_slot:
            security.limits.release()


def run_analysis_in_background(project_id, answers, feedback, llm_slot=False):
    try:
        project = load_project(project_id)
        if project is None or project.get("status") != "analyzing":
            return
        finish_analysis(project, answers=answers, feedback=feedback)
    except Exception:  # noqa: BLE001 - storage itself failed; recovery on restart handles the project
        logger.exception("Business Analyst: could not save the analysis of project %s", project_id)
    finally:
        if llm_slot:
            security.limits.release()


def finish_analysis(project, answers=None, feedback=None, settings=None):
    """Call the Business Analyst and store the result, or a safe error. Never falls back to mock."""
    analysis = project.setdefault("analysis", {})
    previous_requirements = project.get("requirements") if feedback else None
    started = time.monotonic()
    try:
        if settings is None:
            settings = get_ba_settings()  # raises ConfigError for an invalid BA_MODE
        result = analyze(
            idea=project["idea"],
            answers=answers,
            feedback=feedback,
            settings=settings,
            previous_requirements=previous_requirements,
        )
        status = STATUS_FOR_VERDICT[result.status]
    except Exception as exc:  # noqa: BLE001 - every failure becomes a safe, stored error
        failure = describe_failure(exc)
        logger.warning("Business Analyst failed: project %s, mode %s, kind %s, code %s, %s",
                       project["project_id"], analysis.get("mode"), analysis.get("kind"), failure.code, failure.detail)
        project["error"] = failure.as_error()
        previous_status = analysis.get("previous_status")
        # A failed revision keeps the version the user reviewed, so nothing is lost and they can retry.
        project["status"] = previous_status if previous_status and project.get("requirements") else "failed"
        analysis.update(outcome="failed", seconds=round(time.monotonic() - started, 1))
        save_with_timestamp(project)
        return project

    requirements = result.model_dump(mode="json")
    if feedback:
        project["revision"] = {
            "feedback": feedback,
            "at": now_iso(),
            "mode": settings.mode,
            **summarize_revision(previous_requirements, requirements),
        }
    else:
        project.pop("revision", None)  # a new analysis is not a revision of the reviewed version
    project["requirements"] = requirements
    project["status"] = status
    project["compatibility"] = requirements_compatibility(requirements)
    analysis.update(outcome="succeeded", seconds=round(time.monotonic() - started, 1))
    save_with_timestamp(project)
    logger.info("Business Analyst: project %s, mode %s, kind %s, verdict %s, %.1f s",
                project["project_id"], settings.mode, analysis.get("kind"), result.status, analysis["seconds"])
    return project


@app.post("/projects", status_code=201)
def create_project(data: ProjectRequest, background_tasks: BackgroundTasks, user=Depends(current_user),
                   client=Depends(current_client)):
    llm_slot = enforce_limits(user, new_project=True, analysis=True, client=client)
    timestamp = now_iso()
    project = {
        "project_id": str(uuid.uuid4()),
        "owner": user,
        "idea": data.prompt,
        "status": "analyzing",
        "current_agent": "business_analyst",
        "requirements": None,
        "artifacts": [],
        "repair_attempt": 0,
        "metrics": None,
        "error": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    save_project(project)
    return start_analysis(project, background_tasks, "initial", llm_slot=llm_slot)


@app.get("/projects/{project_id}")
def get_project_pipeline(project_id: uuid.UUID, user=Depends(current_user)):
    return get_existing_project(project_id, user)


@app.post("/projects/{project_id}/approve")
def approve_project(
    project_id: uuid.UUID, data: ApprovalRequest, background_tasks: BackgroundTasks, user=Depends(current_user),
    client=Depends(current_client),
):
    get_existing_project(project_id, user)  # 404 for someone else's project, before any limit is counted
    llm_slot = enforce_limits(user, analysis=not data.approved, client=client)
    with _approval_lock:
        project = get_existing_project(project_id, user)
        if project["status"] != "awaiting_approval":
            if llm_slot:
                security.limits.release()
            raise HTTPException(status_code=409, detail="Project is not ready for approval")

        if data.approved:
            # Move to "designing" before answering, so a second approval gets 409.
            # The pipeline itself runs after this response has been sent.
            project["status"] = "designing"
            project["current_agent"] = "software_architect"
            project["requirements_approved"] = True
            project["error"] = None
            save_with_timestamp(project)
            background_tasks.add_task(run_generation, project["project_id"])
            return project

    if not data.feedback:
        raise HTTPException(status_code=422, detail="Feedback is required when requesting changes")
    project["requirements_approved"] = False
    project["feedback"] = data.feedback
    project.setdefault("feedback_history", []).append({"feedback": data.feedback, "at": now_iso()})
    return start_analysis(project, background_tasks, "feedback", answers=project.get("answers"),
                          feedback=data.feedback, llm_slot=llm_slot)

@app.post("/projects/{project_id}/answers")
def submit_answers(project_id: uuid.UUID, data: AnswersRequest, background_tasks: BackgroundTasks,
                   user=Depends(current_user), client=Depends(current_client)):
    project = get_existing_project(project_id, user)
    if project["status"] != "awaiting_clarification":
        raise HTTPException(status_code=409, detail="Project is not awaiting clarification")
    if not data.answers or not any(value.strip() for value in data.answers.values()):
        raise HTTPException(status_code=422, detail="At least one non-empty answer is required")
    llm_slot = enforce_limits(user, analysis=True, client=client)
    # Answers from earlier rounds are kept; a new answer to the same question replaces the old one.
    project["answers"] = {**(project.get("answers") or {}), **data.answers}
    return start_analysis(project, background_tasks, "answers", answers=project["answers"], llm_slot=llm_slot)


def file_response(path, name, headers=None):
    return Response(content=path.read_bytes(), media_type=artifacts.media_type(name), headers=headers)


@app.get("/projects/{project_id}/artifacts/{name}")
def get_artifact(project_id: uuid.UUID, name: str, user=Depends(current_user)):
    """One generated file by its artifact name, e.g. architecture.json or app.js."""
    project = get_existing_project(project_id, user)
    path = artifacts.artifact_file(project["project_id"], name)
    if path is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return file_response(path, name, {"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})


@app.get("/projects/{project_id}/preview", include_in_schema=False)
def redirect_to_preview(project_id: uuid.UUID, user=Depends(current_user)):
    """The app links style.css and app.js relatively, so it must be opened at .../preview/."""
    get_existing_project(project_id, user)
    return RedirectResponse(url=f"/projects/{project_id}/preview/", status_code=307)


@app.get("/projects/{project_id}/preview/")
def preview_app(request: Request, project_id: uuid.UUID, user=Depends(current_user)):
    """The generated application's index.html."""
    return preview_app_file(request, project_id, "index.html", user)


@app.get("/projects/{project_id}/preview/{filename}")
def preview_app_file(request: Request, project_id: uuid.UUID, filename: str, user=Depends(current_user)):
    """A file of the generated application: index.html, style.css or app.js."""
    project = get_existing_project(project_id, user)
    path = artifacts.preview_file(project["project_id"], filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Preview file not found")
    return file_response(path, filename, preview_headers(request))


@app.get("/projects/{project_id}/download")
def download_project(project_id: uuid.UUID, user=Depends(current_user)):
    """ZIP with the generated application and its requirements and architecture."""
    project = get_existing_project(project_id, user)
    missing = artifacts.missing_for_download(project["project_id"])
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"The application is not ready for download. Missing: {', '.join(missing)}",
        )
    filename = f"bunyan-app-{str(project_id)[:8]}.zip"
    return Response(
        content=artifacts.build_zip(project["project_id"]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )


# The production frontend (the built React app), served from the same origin as the API:
# one HTTPS address, no CORS, and the same access control as every other route.
# Mounted last so it never shadows an API route.
FRONTEND_DIR = os.environ.get("BUNYAN_FRONTEND_DIR", "").strip()
if FRONTEND_DIR and Path(FRONTEND_DIR).is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
