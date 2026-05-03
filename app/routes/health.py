import time
import os
from flask import Blueprint, jsonify
from app.core.limiter import health as redis_health
from app.core.limiter import limiter
from app.core.database import Database

health = Blueprint("health", __name__)

APP_VERSION = os.getenv("APP_VERSION", "unknown")
APP_STARTED_AT = time.time()

@health.route('/live', methods=['GET'])
@limiter.exempt
def live():
    return jsonify({"status": "ok"}), 200

@health.route('/ready', methods=['GET'])
@limiter.exempt
def ready():
    mysql = Database.health()
    redis = redis_health()

    redis_healthy = redis["status"] in ("ok", "disabled")
    healthy = mysql["status"] == "ok" and redis_healthy

    return jsonify({"status": "ok" if healthy else "degraded"}), (200 if healthy else 503)

@health.route('/mysql', methods=['GET'])
@limiter.exempt
def health_mysql():
    result = Database.health()
    
    return jsonify(result), (200 if result["status"] == "ok" else 503)


@health.route('/redis', methods=['GET'])
@limiter.exempt
def health_redis():
    result = redis_health()
    ok = result["status"] in ("ok", "disabled")
    
    return jsonify(result), (200 if ok else 503)


@health.route('', methods=['GET'])
@health.route('/', methods=['GET'])
@limiter.exempt
def health_status():
    mysql = Database.health()
    redis = redis_health()
    checks = {"mysql": mysql, "redis": redis}

    healthy = (
        mysql["status"] == "ok"
        and redis["status"] in ("ok", "disabled")
    )

    payload = {
        "status": "ok" if healthy else "degraded",
        "version": APP_VERSION,
        "uptime_seconds": round(time.time() - APP_STARTED_AT, 1),
        "checks": checks,
    }
    
    return jsonify(payload), (200 if healthy else 503)