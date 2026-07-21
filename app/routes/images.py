import os
import uuid

from flask import Blueprint, jsonify, request
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from app.core.limiter import limiter
from app.utils.middleware.authentication import authorize_request

images = Blueprint("images", __name__)

REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")
_redis = Redis.from_url(REDIS_URI)
_image_queue = Queue("images", connection=_redis)


def _build_temp_url(image_id: str) -> str:
    from urllib.parse import urljoin

    return str(urljoin(os.getenv("API_BASE_URL", ""), f"static/temp/{image_id}.webp"))


@images.route("/preview", methods=["POST"])
@limiter.limit("1 per minute")
@authorize_request
def generate_image():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files.get("file", None)

    if (
        file is None
        or not isinstance(file.filename, str)
        or not file.filename.endswith((".png", ".jpg", ".jpeg"))
    ):
        return jsonify(
            {"error": "Unsupported file type. Supported types are PNG, JPG, JPEG."}
        ), 415

    raw = file.read()
    if len(raw) > 4 * 1024 * 1024:
        return jsonify({"error": "File is too large (max 4MB)"}), 413

    ext = os.path.splitext(file.filename)[1].lower()
    raw_id = str(uuid.uuid4())
    raw_path = f"app/static/temp/process/{raw_id}{ext}"
    with open(raw_path, "wb") as f:
        f.write(raw)

    job = _image_queue.enqueue(
        "app.services.image_processing.process_image",
        raw_path,
        job_timeout=180,
        result_ttl=600,
        failure_ttl=600,
    )

    return jsonify({"job_id": job.id}), 202


@images.route("/preview/<job_id>", methods=["GET"])
@limiter.limit("30 per minute")
@authorize_request
def get_preview_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=_redis)
    except NoSuchJobError:
        return jsonify({"status": "not_found"}), 404

    status = job.get_status()

    if status == "finished":
        result = job.return_value()
        if not isinstance(result, dict):
            return jsonify({"status": "not_found"}), 404
        return jsonify(
            {
                "status": "ready",
                "image_id": result["image_id"],
                "image_color": result["dominant_hexcode"],
                "image_category": result["category"],
                "image_sub_category": result["sub_category"],
                "image_url": _build_temp_url(result["image_id"]),
                "image_seasons": [],
                "image_tags": [],
            }
        ), 200

    if status == "failed":
        latest = job.latest_result()
        exc = (latest.exc_string if latest is not None else "") or ""
        if "ImageUnclearError" in exc:
            return jsonify(
                {
                    "status": "failed",
                    "error": "The provided image does not contain a clear foreground.",
                }
            ), 422
        return jsonify({"status": "failed", "error": "Processing failed."}), 500

    return jsonify({"status": "processing"}), 200
