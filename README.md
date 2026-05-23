# College Club Event Management System

A complete web application for managing college clubs, events, participants, and registrations — built with **Python (Flask)** and **MySQL**.

---

## Features

- **Admin Login** with secure password hashing (werkzeug)
- **Dashboard** with stat cards, upcoming events, recent registrations, and latest notices
- **Clubs** — Add, edit, delete, view details with all events
- **Events** — Search, filter (upcoming/past/all), manage registrations, mark attendance, issue certificates, export CSV
- **Participants** — Full CRUD with registration history
- **Registrations** — Status flow: `registered → attended → certificate_issued`
- **Notices** — Post and delete announcements
- **Settings** — Change password, update college name
- **Responsive sidebar** with mobile collapse
- **Purple theme** throughout with Bootstrap 5

---

## Quick Start

### 1. Clone / download the project

### 2. Create a virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
copy .env.example .env       # Windows
cp .env.example .env         # macOS/Linux
```
Edit `.env` and set your MySQL credentials.

### 5. Set up the database
```bash
mysql -u root -p < schema.sql
```

### 6. Seed the default admin
```bash
python seed_admin.py
```
Default credentials: `admin@clubevents.com` / `admin123`

### 7. Run the app
```bash
python app.py
```
Open [http://localhost:5000](http://localhost:5000)

---

## File Structure

```
├── app.py                  # Main Flask application
├── schema.sql              # Database schema + sample data
├── seed_admin.py           # Seeds the default admin account
├── requirements.txt
├── Procfile
├── .env.example
├── .gitignore
├── README.md
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── clubs.html
│   ├── club_detail.html
│   ├── add_club.html
│   ├── events.html
│   ├── event_detail.html
│   ├── add_event.html
│   ├── participants.html
│   ├── participant_detail.html
│   ├── add_participant.html
│   ├── registrations.html
│   ├── notices.html
│   └── settings.html
└── static/
    ├── css/custom.css
    └── js/main.js
```

---

## Database Tables

| Table | Description |
|-------|-------------|
| `admins` | Admin accounts |
| `clubs` | College clubs |
| `events` | Events per club |
| `participants` | Student participants |
| `registrations` | Event registrations with status |
| `notices` | Announcements |
| `settings` | Key-value app settings |

---

## Security

- All routes protected with `@login_required`
- Passwords hashed with `werkzeug.security`
- DB credentials in `.env` (never committed)
- Parameterized SQL queries throughout
