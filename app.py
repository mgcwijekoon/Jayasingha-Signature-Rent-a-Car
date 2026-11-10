"""Jayasingha Signature & Rent-a-Car — Flask application.

This is a beginner-friendly development build. Before public deployment, set
FLASK_SECRET_KEY, ADMIN_USERNAME, and ADMIN_PASSWORD to secure environment
values and run with FLASK_DEBUG=0.
"""

from datetime import date, datetime
from hmac import compare_digest
import os
import re
import sqlite3
from urllib.parse import quote

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "bookings.db"))

app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY", "development-only-change-this-before-deployment"
)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "12345")
WHATSAPP_NUMBER = re.sub(
    r"\D", "", os.environ.get("WHATSAPP_NUMBER", "94772578592")
)

# Keep the names and rates aligned with the cars shown on the website.
CAR_OPTIONS = [
    {
        "name": "Toyota Aqua",
        "image": "images/aqua-1.jpeg",
        "price": 10000,
        "type": "hybrid",
        "seats": 5,
        "best_for": "City trips and fuel-conscious travel",
        "description": "A compact hybrid choice for daily trips and easier city driving.",
    },
    {
        "name": "Toyota Prius",
        "image": "images/prius-placeholder.svg",
        "price": 12000,
        "type": "hybrid",
        "seats": 5,
        "best_for": "Comfortable everyday and business travel",
        "description": "A comfortable hybrid option for longer everyday journeys.",
    },
    {
        "name": "Honda GS1",
        "image": "images/honda-gs1-placeholder.svg",
        "price": 9000,
        "type": "petrol",
        "seats": 5,
        "best_for": "Value-focused daily travel",
        "description": "A practical option when keeping the daily rental rate low is a priority.",
    },
    {
        "name": "Honda Vezel",
        "image": "images/vezel-placeholder.svg",
        "price": 12000,
        "type": "hybrid",
        "seats": 5,
        "best_for": "Family and weekend journeys",
        "description": "A crossover-style option for a comfortable family or weekend journey.",
    },
    {
        "name": "Honda Civic",
        "image": "images/civic-placeholder.svg",
        "price": 12000,
        "type": "petrol",
        "seats": 5,
        "best_for": "Business and city travel",
        "description": "A stylish sedan option for business and everyday travel.",
    },
]
CAR_NAMES = {item["name"] for item in CAR_OPTIONS}
CAR_PRICES = {item["name"]: item["price"] for item in CAR_OPTIONS}


def get_db():
    """Return a SQLite connection whose database path is project-relative."""
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the booking table and add any newer columns to old databases."""
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                car TEXT NOT NULL,
                pickup_location TEXT NOT NULL DEFAULT '',
                pickup TEXT NOT NULL,
                pickup_time TEXT NOT NULL DEFAULT '',
                return_date TEXT NOT NULL,
                days INTEGER NOT NULL DEFAULT 0,
                km REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Pending'
            )
            """
        )
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(bookings)")
        }
        migrations = {
            "pickup_location": "TEXT NOT NULL DEFAULT ''",
            "pickup_time": "TEXT NOT NULL DEFAULT ''",
            "days": "INTEGER NOT NULL DEFAULT 0",
            "km": "REAL NOT NULL DEFAULT 0",
            "status": "TEXT NOT NULL DEFAULT 'Pending'",
        }
        for column, definition in migrations.items():
            if column not in columns:
                conn.execute(
                    f"ALTER TABLE bookings ADD COLUMN {column} {definition}"
                )
        conn.commit()
    finally:
        conn.close()


def parse_booking_dates(pickup_text, return_text):
    """Parse ISO dates and ensure the return date is after pickup."""
    try:
        pickup_day = date.fromisoformat(pickup_text)
        return_day = date.fromisoformat(return_text)
    except (TypeError, ValueError):
        return None, None, "Please enter valid pickup and return dates."

    if return_day <= pickup_day:
        return None, None, "Return date must be after the pickup date."
    if pickup_day < date.today():
        return None, None, "Pickup date cannot be in the past."

    return pickup_day, return_day, None


def find_overlapping_booking(conn, car, pickup_text, return_text):
    """Find a non-cancelled booking overlapping the selected date range."""
    return conn.execute(
        """
        SELECT id
        FROM bookings
        WHERE car = ?
          AND LOWER(status) != 'cancelled'
          AND pickup < ?
          AND return_date > ?
        LIMIT 1
        """,
        (car, return_text, pickup_text),
    ).fetchone()


def booking_page(error=None, selected_car="", form_data=None):
    return render_template(
        "booking.html",
        error=error,
        selected_car=selected_car,
        form_data=form_data or {},
        success=False,
    )


@app.route("/")
def home():
    return render_template("index.html")

    car_data = [
        {
            "name": "Toyota Aqua",
            "price": 10000,
            "description": "Fuel-efficient hybrid for comfortable city journeys.",
            "type": "hybrid",
            "seats": 5,
            "image": "images/aqua-1.jpeg"
        },
        {
            "name": "Toyota Prius",
            "price": 10000,
            "description": "Comfortable hybrid for everyday travel.",
            "type": "hybrid",
            "seats": 5,
            "image": ""
        },
        {
            "name": "Honda GS1",
            "price": 10000,
            "description": "A comfortable option for your next journey.",
            "type": "standard",
            "seats": 5,
            "image": ""
        }
    ]

    return render_template(
        "index.html",
        car_data=car_data
    )

@app.route("/trip-planner")
def trip_planner():
    return render_template("trip_planner.html", car_data=CAR_OPTIONS)


@app.route("/api/check-availability")
def check_availability():
    car = request.args.get("car", "").strip()
    pickup_text = request.args.get("pickup", "").strip()
    return_text = request.args.get("return_date", "").strip()

    if car not in CAR_NAMES:
        return jsonify({"available": False, "message": "Please select a valid car."}), 400

    pickup_day, return_day, date_error = parse_booking_dates(pickup_text, return_text)
    if date_error:
        return jsonify({"available": False, "message": date_error}), 400

    conn = get_db()
    try:
        conflict = find_overlapping_booking(
            conn, car, pickup_day.isoformat(), return_day.isoformat()
        )
    except sqlite3.Error:
        app.logger.exception("Unable to check vehicle availability")
        return jsonify(
            {"available": False, "message": "Unable to check availability right now."}
        ), 500
    finally:
        conn.close()

    if conflict:
        return jsonify(
            {"available": False, "message": f"{car} is already booked for those dates."}
        )

    return jsonify({"available": True, "message": f"{car} is available for those dates."})


@app.route("/booking", methods=["GET", "POST"])
def booking():
    if request.method == "GET":
        return render_template(
            "booking.html",
            selected_car=request.args.get("car", "").strip(),
            form_data={
                "pickup": request.args.get("pickup", ""),
                "return_date": request.args.get("return_date", ""),
            },
            success=False,
        )

    form_data = request.form.to_dict()
    name = form_data.get("name", "").strip()
    phone = form_data.get("phone", "").strip()
    car = form_data.get("car", "").strip()
    pickup_location = form_data.get("pickup_location", "").strip()
    pickup_text = form_data.get("pickup", "").strip()
    pickup_time = form_data.get("pickup_time", "").strip()
    return_text = form_data.get("return_date", "").strip()
    km_text = form_data.get("km", "").strip()

    if not name or not phone or not car or not pickup_location or not pickup_time:
        return booking_page("Please complete all required fields.", car, form_data)
    if len(name) > 100 or len(pickup_location) > 180:
        return booking_page("Please shorten the name or pickup location.", car, form_data)
    if car not in CAR_NAMES:
        return booking_page("Please select a valid vehicle.", car, form_data)

    phone_digits = re.sub(r"\D", "", phone)
    if len(phone_digits) < 9 or len(phone_digits) > 15:
        return booking_page("Please enter a valid phone number.", car, form_data)

    pickup_day, return_day, date_error = parse_booking_dates(pickup_text, return_text)
    if date_error:
        return booking_page(date_error, car, form_data)

    try:
        km = float(km_text)
        if km < 0 or km > 1_000_000:
            raise ValueError
    except (TypeError, ValueError):
        return booking_page("Enter a valid estimated distance in kilometres.", car, form_data)

    days = (return_day - pickup_day).days
    pickup_text = pickup_day.isoformat()
    return_text = return_day.isoformat()

    # A write lock prevents two simultaneous requests from both passing the
    # availability check and reserving the same car/date window.
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conflict = find_overlapping_booking(conn, car, pickup_text, return_text)
        if conflict:
            conn.rollback()
            return booking_page(
                f"{car} is already booked for those dates. Please choose another date or car.",
                car,
                form_data,
            )

        cursor = conn.execute(
            """
            INSERT INTO bookings
                (name, phone, car, pickup_location, pickup, pickup_time,
                 return_date, days, km, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
            """,
            (
                name,
                phone,
                car,
                pickup_location,
                pickup_text,
                pickup_time,
                return_text,
                days,
                km,
            ),
        )
        booking_id = cursor.lastrowid
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        app.logger.exception("Could not save a booking")
        return booking_page(
            "We could not save the booking just now. Please try again.", car, form_data
        ), 500
    finally:
        conn.close()

    message = (
        "🚗 New Jayasingha Signature booking request\n\n"
        f"Booking ID: {booking_id}\n"
        f"Full Name: {name}\n"
        f"Phone: {phone}\n"
        f"Car: {car}\n"
        f"Pickup Location: {pickup_location}\n"
        f"Pickup Date: {pickup_text}\n"
        f"Pickup Time: {pickup_time}\n"
        f"Return Date: {return_text}\n"
        f"Number of Days: {days}\n"
        f"Estimated Distance: {km:g} km\n"
        f"Estimated Rental: Rs. {CAR_PRICES[car] * days:,.0f} (subject to confirmation)"
    )
    whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(message)}"

    return render_template(
        "booking.html",
        success=True,
        whatsapp_url=whatsapp_url,
        booking_id=booking_id,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if compare_digest(username, ADMIN_USERNAME) and compare_digest(password, ADMIN_PASSWORD):
            session.clear()
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        return render_template("login.html", error="Invalid username or password."), 401
    return render_template("login.html")


@app.route("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))

    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()
    if status_filter and status_filter not in {"Pending", "Confirmed", "Cancelled"}:
        status_filter = ""

    conn = get_db()
    try:
        query = "SELECT * FROM bookings WHERE 1=1"
        params = []
        if search:
            query += " AND (name LIKE ? OR phone LIKE ? OR car LIKE ? OR pickup_location LIKE ?)"
            search_value = f"%{search}%"
            params.extend([search_value] * 4)
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        query += " ORDER BY id DESC"
        bookings = conn.execute(query, params).fetchall()

        counts = {}
        for status in ("Pending", "Confirmed", "Cancelled"):
            counts[status] = conn.execute(
                "SELECT COUNT(*) FROM bookings WHERE status = ?", (status,)
            ).fetchone()[0]
        total_bookings = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    finally:
        conn.close()

    return render_template(
        "admin.html",
        bookings=bookings,
        total_bookings=total_bookings,
        pending_bookings=counts["Pending"],
        confirmed_bookings=counts["Confirmed"],
        cancelled_bookings=counts["Cancelled"],
        search=search,
        status_filter=status_filter,
    )


@app.route("/admin/update-status/<int:booking_id>", methods=["POST"])
def update_status(booking_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    status = request.form.get("status", "")
    if status not in {"Pending", "Confirmed", "Cancelled"}:
        return redirect(url_for("admin"))

    conn = get_db()
    try:
        conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/delete/<int:booking_id>", methods=["POST"])
def delete_booking(booking_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    conn = get_db()
    try:
        conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for("admin"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    debug_enabled = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=debug_enabled)
