# Jayasingha Signature & Rent-a-Car — Stage 1 Upgrade

A Flask and SQLite car-rental website with a cinematic home page, five-vehicle fleet, date-aware booking, admin booking management, and a new Smart Trip Planner.

## What changed in this upgrade

- Added **Smart Trip Planner** at `/trip-planner`. Customers can choose a journey style, passenger count, daily budget, hybrid preference, and optional dates to receive ranked vehicle suggestions.
- Fixed local Aqua photo filenames and corrected the gallery to the three Aqua photographs supplied with the original project.
- Replaced missing car image links with local model-labelled illustration placeholders, so the home page and fleet page no longer show broken images for cars whose photos have not been supplied yet.
- Added today's booking status on the fleet page.
- Consolidated the availability endpoint into one active route and removed the orphaned duplicate code that was below `app.run()`.
- Added server-side booking validation and a second availability check before the booking is saved. This is important because browser-side validation alone can be bypassed.
- Kept form values on the page after validation errors.
- Made the SQLite path relative to `app.py`, so the app can be started from the project folder without accidentally creating the database in a different current directory.
- Configured the WhatsApp contact as an environment setting with a local-development default.

## Run on Windows (VS Code)

1. Extract this ZIP into a normal folder, for example `Desktop\Jayasingha Signature Stage 1`.
2. Open that folder in VS Code.
3. Open **Terminal → New Terminal** and run:

   ```powershell
   py -m venv venv
   .\venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python app.py
   ```

4. Open `http://127.0.0.1:5000` in your browser. Keep the VS Code terminal running while you use the site.
5. Open `http://127.0.0.1:5000/trip-planner` to test the new feature.
6. Open `http://127.0.0.1:5000/login` for the admin login. The local demo defaults are username `admin` and password `12345`.
7. Optional: run the basic checks with `python -m unittest discover -s tests`.

The SQLite file `bookings.db` is created automatically beside `app.py` the first time the server starts.

## Local configuration

The project works locally without extra configuration. For a stronger local/admin password, set environment variables in the same PowerShell terminal **before** running the app:

```powershell
$env:FLASK_SECRET_KEY = "replace-with-a-long-random-secret"
$env:ADMIN_USERNAME = "your-admin-username"
$env:ADMIN_PASSWORD = "your-strong-password"
$env:WHATSAPP_NUMBER = "947XXXXXXXX"
python app.py
```

Set `WHATSAPP_NUMBER` to the business WhatsApp number in international format, with digits only (for example, Sri Lanka numbers start with `94` and omit the leading `0`). Replace the example with the intended business number.

> **Important:** This is a development-stage project, not yet a public production deployment. Before putting it on the internet, set private secret/admin values, set `$env:FLASK_DEBUG = "0"`, add CSRF protection and HTTPS, and review admin authentication and hosting configuration.

## Vehicle photos

The original ZIP contained three Aqua photos, with doubled/misspelled extensions, and did not contain separate Prius, Honda GS1, Vezel, or Civic photos. The Aqua filenames have been corrected. The other models use local illustration placeholders so the site stays complete. Replace these files with approved photographs when available:

- `static/images/prius-placeholder.svg`
- `static/images/honda-gs1-placeholder.svg`
- `static/images/vezel-placeholder.svg`
- `static/images/civic-placeholder.svg`

Keep the same filenames if you replace the SVGs with corresponding image files, or update the paths in `templates/index.html`, `templates/cars.html`, and `app.py`.

## Project structure

```text
Jayasingha_Signature_Stage1/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── tests/
│   └── test_app.py
├── bookings.db             # created when the app runs
├── templates/
│   ├── index.html
│   ├── cars.html
│   ├── booking.html
│   ├── trip_planner.html
│   ├── login.html
│   └── admin.html
└── static/
    ├── images/
    └── videos/
        └── hero.mp4
```
