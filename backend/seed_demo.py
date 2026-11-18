"""Fills an empty StudBud database with demo data: courses, communities, an administrator,
a moderator and a handful of students with profiles, posts and connections.

    python seed_demo.py

Safe to run twice: it stops if the demo accounts already exist. Every demo account uses the
password shown at the end, so this must never be run against a real database.
"""
from werkzeug.security import generate_password_hash

from app import create_app
from app.container import get_deps, get_service
from app.models import Account, AccountStatus, Role

PASSWORD = "Demo1234"
COURSES = [("SWEN-261", "Introduction to Software Engineering"), ("CSEC-140", "Computing Security Principles"),
           ("MATH-181", "Calculus I"), ("PHIL-202", "Foundations of Moral Philosophy"), ("ANTH-220", "Language and Culture")]
INTERESTS = ["Football", "Photography", "Gaming", "Music"]
# name, email, role, intent, cohort, year, interests, courses
PEOPLE = [
    ("Admin", "admin@g.rit.edu", Role.ADMINISTRATOR, "friendship", "neither", 4, [], []),
    ("Moderator", "moderator@g.rit.edu", Role.MODERATOR, "friendship", "neither", 4, ["Music"], ["SWEN-261"]),
    ("Amira", "amira@g.rit.edu", Role.STUDENT, "study partner", "first year", 1, ["Photography", "Music"], ["SWEN-261", "MATH-181"]),
    ("Omar", "omar@g.rit.edu", Role.STUDENT, "both", "international", 2, ["Football", "Gaming"], ["SWEN-261", "CSEC-140"]),
    ("Layla", "layla@g.rit.edu", Role.STUDENT, "friendship", "first year", 1, ["Music"], ["PHIL-202", "ANTH-220"]),
    ("Yusuf", "yusuf@g.rit.edu", Role.STUDENT, "study partner", "both", 3, ["Gaming"], ["CSEC-140", "MATH-181"]),
    ("Noor", "noor@g.rit.edu", Role.STUDENT, "both", "international", 1, ["Photography"], ["SWEN-261", "ANTH-220"]),
]


def main():
    app = create_app()
    with app.app_context():
        d = get_deps()
        if d.accounts.find_by_email("admin@g.rit.edu"):
            print("Demo data is already there. Nothing changed.")
            return
        ids = {}
        for name, email, role, *_ in PEOPLE:
            a = d.accounts.add(Account(email, name, generate_password_hash(PASSWORD, method="pbkdf2:sha256"),
                                       status=AccountStatus.VERIFIED, role=role))
            ids[name] = a.id
        admin, comm, prof, conn, _ = (get_service(n) for n in ("admin", "communities", "profiles", "connections", "moderation"))
        for code, title in COURSES:
            assert admin.add_course(ids["Admin"], code, title).ok
        for name in INTERESTS:
            assert admin.create_interest_community(ids["Admin"], name).ok
        for name, _e, _r, intent, cohort, year, interests, courses in PEOPLE:
            res = prof.save(ids[name], intent, cohort, year, interests, courses)
            assert res.ok, res.errors
        by_name = {c.name: c.id for c, _joined in comm.list_for(ids["Amira"])}
        for name in ("Amira", "Omar", "Noor"):
            comm.join(ids[name], by_name["Photography"] if name != "Omar" else by_name["Football"])
        swen = next(i for n, i in by_name.items() if n.startswith("SWEN-261"))
        comm.create_post(ids["Amira"], swen, "question", "Who is free to review the SRS?", "Looking for a study partner before Friday.")
        post = comm.create_post(ids["Omar"], swen, "study partner request", "Study group for SWEN-261", "Libraries on Tuesday evenings work for me.")
        comm.reply(ids["Noor"], post.item.id, "I would like to join.")
        sent = conn.send_request(ids["Amira"], ids["Omar"], "Saw your study group post.")
        conn.respond(sent.connection.id, ids["Omar"], True)
        conn.send_request(ids["Noor"], ids["Omar"], "")
    print(f"Demo data added. Sign in with any of these emails and the password {PASSWORD}:")
    for name, email, role, *_ in PEOPLE:
        print(f"  {email}  ({role.value})")


if __name__ == "__main__":
    main()
