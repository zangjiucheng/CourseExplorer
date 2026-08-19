from __future__ import annotations

import os

from flask import Flask, jsonify, request, send_from_directory

from uw_course.web.services import CourseService, ScheduleSelection, normalize_course_code

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def create_app() -> Flask:
    # static_url_path="" serves files from the static folder at the root URL
    # so Vite's /assets/... paths resolve correctly
    app = Flask(__name__, static_folder=_STATIC_DIR, static_url_path="")
    service = CourseService()

    @app.get("/")
    def index():
        if not os.path.exists(os.path.join(_STATIC_DIR, "index.html")):
            return (
                "<h1>UW Course Planner</h1>"
                "<p>The web interface has not been built yet. Build the frontend with "
                "<code>scripts/build_frontend.sh</code> (or "
                "<code>npm --prefix frontend ci &amp;&amp; npm --prefix frontend run build</code>) "
                "before running the server, or install the published package from PyPI.</p>",
                500,
            )
        return send_from_directory(_STATIC_DIR, "index.html")

    @app.get("/api/terms")
    def list_terms():
        return jsonify({"terms": service.list_terms()})

    @app.get("/api/courses")
    def search_courses():
        term = request.args.get("term", "").strip()
        query = request.args.get("q", "").strip()
        if not term:
            return jsonify({"error": "Missing term"}), 400
        return jsonify({"results": service.search_courses(term, query)})

    @app.get("/api/courses/<path:course_code>")
    def get_course(course_code: str):
        term = request.args.get("term", "").strip()
        if not term:
            return jsonify({"error": "Missing term"}), 400
        return jsonify(service.get_course(term, normalize_course_code(course_code)))

    @app.post("/api/schedule")
    def build_schedule():
        payload = request.get_json(silent=True) or {}
        term = (payload.get("term") or "").strip()
        if not term:
            return jsonify({"error": "Missing term"}), 400

        selections = [
            ScheduleSelection(
                course_code=normalize_course_code(item.get("course_code", "")),
                class_id=item.get("class_id"),
            )
            for item in payload.get("selections", [])
            if item.get("course_code")
        ]
        return jsonify(service.build_schedule(term, selections))

    @app.post("/api/plan/parse")
    def parse_plan():
        payload = request.get_json(silent=True) or {}
        plan_text = payload.get("plan_text", "")
        try:
            parsed = service.parse_plan_text(plan_text)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(parsed)

    @app.post("/api/plan/export")
    def export_plan():
        payload = request.get_json(silent=True) or {}
        term = (payload.get("term") or "").strip()
        if not term:
            return jsonify({"error": "Missing term"}), 400
        selections = [
            ScheduleSelection(
                course_code=normalize_course_code(item.get("course_code", "")),
                class_id=item.get("class_id"),
            )
            for item in payload.get("selections", [])
            if item.get("course_code")
        ]
        return jsonify({"plan_text": service.export_plan_text(term, selections)})

    @app.post("/api/plan/resolve")
    def resolve_plan():
        payload = request.get_json(silent=True) or {}

        if "plan_text" in payload:
            try:
                parsed = service.parse_plan_text(payload.get("plan_text", ""))
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
            term = parsed["term"]
            raw_selections = parsed.get("selections", [])
        else:
            term = (payload.get("term") or "").strip()
            if not term:
                return jsonify({"error": "Missing term"}), 400
            raw_selections = payload.get("selections", [])

        selections = [
            ScheduleSelection(
                course_code=normalize_course_code(item.get("course_code", "")),
                class_id=item.get("class_id"),
            )
            for item in raw_selections
            if item.get("course_code")
        ]
        return jsonify(service.resolve_plan(term, selections))

    return app


def run_app(host: str = "127.0.0.1", port: int = 31415, debug: bool = False) -> None:
    create_app().run(host=host, port=port, debug=debug)
