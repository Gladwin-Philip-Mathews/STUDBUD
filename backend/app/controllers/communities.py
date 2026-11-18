"""Community, post and reply endpoints (process 3.0). No rules here: each route calls one CommunityService operation."""
from flask import Blueprint, g, jsonify, request

from ..container import get_service
from ..models.enums import Role
from ..security import profile_required, role_required

bp = Blueprint("communities", __name__, url_prefix="/api")

NOT_FOUND = ({"message": "Not found."}, 404)


def _svc():
    return get_service("communities")


def _page():
    try:
        return max(int(request.args.get("page", 1)), 1)
    except ValueError:
        return 1


def post_json(p, viewer_id, replies=None, community_name=None):
    s = _svc()
    out = {"id": p.id, "communityId": p.community_id, "kind": p.kind, "title": p.title, "text": p.body,
           "status": p.status, "createdAt": p.created_at.isoformat(), "edited": p.edited_at is not None,
           "author": {"id": p.author_id, "displayName": s.author_name(p.author_id)},
           "mine": p.author_id == viewer_id}
    if p.status == "hidden":
        out["notice"] = "A moderator has hidden this post. Only you can see it."  # FR-065
    if community_name:
        out["community"] = community_name
    if replies is not None:
        out["replies"] = [reply_json(r, viewer_id) for r in replies]
    return out


def reply_json(r, viewer_id):
    out = {"id": r.id, "postId": r.post_id, "text": r.body, "status": r.status, "createdAt": r.created_at.isoformat(),
           "edited": r.edited_at is not None, "author": {"id": r.author_id, "displayName": _svc().author_name(r.author_id)},
           "mine": r.author_id == viewer_id}
    if r.status == "hidden":
        out["notice"] = "A moderator has hidden this reply. Only you can see it."
    return out


def community_json(c, joined):
    return {"id": c.id, "name": c.name, "kind": c.kind, "memberCount": c.member_count, "joined": joined,
            "courseCode": c.course_code,
            "notice": "Posts and study partnerships must follow the course collaboration rules." if c.kind == "course" else None}


def _errors(result):
    if result.not_found:
        return jsonify(NOT_FOUND[0]), 404
    return jsonify({"errors": result.errors}), 400


@bp.get("/communities")
@profile_required
def communities():
    found = _svc().list_for(g.account.id, request.args.get("q", ""))
    return jsonify({"communities": [community_json(c, j) for c, j in found]})


@bp.post("/communities")
@role_required(Role.ADMINISTRATOR)
def create_interest():
    result = _svc().create_interest_community((request.get_json(silent=True) or {}).get("name"))
    if not result.ok:
        return _errors(result)
    return jsonify({"community": community_json(result.item, False)}), 201


@bp.post("/communities/<int:cid>/join")
@profile_required
def join(cid):
    if not _svc().join(g.account.id, cid):
        return jsonify({"message": "You cannot join this community."}), 400
    return jsonify({"message": "Joined."})


@bp.post("/communities/<int:cid>/leave")
@profile_required
def leave(cid):
    _svc().leave(g.account.id, cid)
    return jsonify({"message": "Left."})


def _paged(result, viewer_id, empty_message):
    if result is None:
        return jsonify(NOT_FOUND[0]), 404
    posts, more = result
    return jsonify({"posts": [post_json(p, viewer_id) for p in posts], "hasMore": more,
                    "message": None if posts else empty_message})


@bp.get("/communities/<int:cid>/posts")
@profile_required
def community_posts(cid):
    return _paged(_svc().community_posts(g.account.id, cid, request.args.get("kind") or None, _page()),
                  g.account.id, "No posts yet.")


@bp.post("/communities/<int:cid>/posts")
@profile_required
def create_post(cid):
    d = request.get_json(silent=True) or {}
    result = _svc().create_post(g.account.id, cid, d.get("kind"), d.get("title"), d.get("text"))
    if not result.ok:
        return _errors(result)
    return jsonify({"post": post_json(result.item, g.account.id)}), 201


@bp.get("/feed")
@profile_required
def feed():
    posts, more = _svc().feed(g.account.id, request.args.get("kind") or None, _page())
    return jsonify({"posts": [post_json(p, g.account.id) for p in posts], "hasMore": more,
                    "message": None if posts else "No posts yet. Join a community to see posts here."})


@bp.get("/search")
@profile_required
def search():
    result = _svc().search(g.account.id, request.args.get("q", ""), request.args.get("kind") or None, _page())
    if result is None:
        return jsonify({"message": "Enter at least 2 characters."}), 400
    posts, more = result
    return jsonify({"posts": [post_json(p, g.account.id) for p in posts], "hasMore": more,
                    "message": None if posts else "No posts found."})


@bp.get("/posts/<int:pid>")
@profile_required
def get_post(pid):
    found = _svc().get_post(g.account.id, pid)
    if found is None:
        return jsonify(NOT_FOUND[0]), 404
    post, replies = found
    return jsonify({"post": post_json(post, g.account.id, replies)})


@bp.put("/posts/<int:pid>")
@profile_required
def edit_post(pid):
    d = request.get_json(silent=True) or {}
    result = _svc().edit_post(g.account.id, pid, d.get("title"), d.get("text"))
    return (jsonify({"post": post_json(result.item, g.account.id)}), 200) if result.ok else _errors(result)


@bp.delete("/posts/<int:pid>")
@profile_required
def delete_post(pid):
    return (jsonify({"message": "Deleted."}), 200) if _svc().delete_post(g.account.id, pid) else (jsonify(NOT_FOUND[0]), 404)


@bp.post("/posts/<int:pid>/replies")
@profile_required
def reply(pid):
    result = _svc().reply(g.account.id, pid, (request.get_json(silent=True) or {}).get("text"))
    return (jsonify({"reply": reply_json(result.item, g.account.id)}), 201) if result.ok else _errors(result)


@bp.put("/replies/<int:rid>")
@profile_required
def edit_reply(rid):
    result = _svc().edit_reply(g.account.id, rid, (request.get_json(silent=True) or {}).get("text"))
    return (jsonify({"reply": reply_json(result.item, g.account.id)}), 200) if result.ok else _errors(result)


@bp.delete("/replies/<int:rid>")
@profile_required
def delete_reply(rid):
    return (jsonify({"message": "Deleted."}), 200) if _svc().delete_reply(g.account.id, rid) else (jsonify(NOT_FOUND[0]), 404)
