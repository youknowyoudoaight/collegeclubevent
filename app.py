import os
import csv
import io
import logging
from datetime import datetime
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, g, make_response)
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey_change_in_production')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

# ─────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        host     = os.getenv('MYSQLHOST')     or os.getenv('DB_HOST', 'localhost')
        port     = int(os.getenv('MYSQLPORT') or os.getenv('DB_PORT', 3306))
        user     = os.getenv('MYSQLUSER')     or os.getenv('DB_USER', 'root')
        password = os.getenv('MYSQLPASSWORD') or os.getenv('DB_PASSWORD', '')
        database = os.getenv('MYSQLDATABASE') or os.getenv('DB_NAME', 'club_events_db')

        logger.info(f"DB connect → host={host} port={port} user={user} db={database}")
        try:
            g.db = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                autocommit=False,
                connection_timeout=10,
            )
            logger.info("DB connection successful")
        except Exception as e:
            logger.error(f"DB connection FAILED: {e}")
            raise
    return g.db


def query_db(sql, args=(), one=False):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(sql, args)
    rv = cursor.fetchall()
    cursor.close()
    return (rv[0] if rv else None) if one else rv


def execute_db(sql, args=()):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(sql, args)
    db.commit()
    last_id = cursor.lastrowid
    cursor.close()
    return last_id


@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ─────────────────────────────────────────────
# Flask-Login User model
# ─────────────────────────────────────────────

class Admin(UserMixin):
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    row = query_db('SELECT id, name, email FROM admins WHERE id = %s', (user_id,), one=True)
    if row:
        return Admin(row['id'], row['name'], row['email'])
    return None


# ─────────────────────────────────────────────
# Context processor
# ─────────────────────────────────────────────

@app.context_processor
def inject_globals():
    college_name = 'College Club Portal'
    try:
        row = query_db("SELECT value FROM settings WHERE `key` = 'college_name'", one=True)
        if row:
            college_name = row['value']
    except Exception:
        pass
    return dict(college_name=college_name, now=datetime.now())


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.route('/health')
def health():
    """Public diagnostic route — shows DB connection status."""
    status = {}
    # Check env vars (mask password)
    status['MYSQLHOST']     = os.getenv('MYSQLHOST', 'NOT SET')
    status['MYSQLPORT']     = os.getenv('MYSQLPORT', 'NOT SET')
    status['MYSQLUSER']     = os.getenv('MYSQLUSER', 'NOT SET')
    status['MYSQLDATABASE'] = os.getenv('MYSQLDATABASE', 'NOT SET')
    status['MYSQLPASSWORD'] = '***' if os.getenv('MYSQLPASSWORD') else 'NOT SET'
    status['SECRET_KEY']    = 'SET' if os.getenv('SECRET_KEY') else 'NOT SET (using default)'

    # Try DB connection
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        cursor.close()
        status['db_connection'] = 'OK'

        # Check if tables exist
        cursor2 = db.cursor()
        cursor2.execute("SHOW TABLES")
        tables = [row[0] for row in cursor2.fetchall()]
        cursor2.close()
        status['tables'] = tables if tables else 'NO TABLES — run /init-db first'
    except Exception as e:
        status['db_connection'] = f'FAILED: {str(e)}'

    rows = ''.join(f'<tr><td><b>{k}</b></td><td>{v}</td></tr>' for k, v in status.items())
    color = 'green' if status.get('db_connection') == 'OK' else 'red'
    return f'''
    <h2 style="font-family:sans-serif;color:{color}">Health Check</h2>
    <table style="font-family:monospace;border-collapse:collapse">
    <tr><th style="text-align:left;padding:6px 16px 6px 0">Key</th>
        <th style="text-align:left">Value</th></tr>
    {rows}
    </table>
    <p style="font-family:sans-serif">
      If tables are missing → visit
      <a href="/init-db?token={os.getenv('SECRET_KEY','')}">/init-db?token=YOUR_SECRET_KEY</a>
    </p>
    '''


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        row = query_db('SELECT * FROM admins WHERE email = %s', (email,), one=True)
        if row and check_password_hash(row['password_hash'], password):
            user = Admin(row['id'], row['name'], row['email'])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid email or password. Please try again.'
    return render_template('login.html', error=error)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    total_clubs = query_db('SELECT COUNT(*) AS cnt FROM clubs', one=True)['cnt']
    total_events = query_db('SELECT COUNT(*) AS cnt FROM events', one=True)['cnt']
    total_participants = query_db('SELECT COUNT(*) AS cnt FROM participants', one=True)['cnt']
    total_registrations = query_db('SELECT COUNT(*) AS cnt FROM registrations', one=True)['cnt']

    upcoming_events = query_db("""
        SELECT e.id, e.event_name, c.club_name, e.event_date, e.venue,
               e.max_participants,
               COUNT(r.id) AS registered_count,
               (e.max_participants - COUNT(r.id)) AS slots_left
        FROM events e
        JOIN clubs c ON e.club_id = c.id
        LEFT JOIN registrations r ON e.id = r.event_id
        WHERE e.event_date >= CURDATE()
        GROUP BY e.id
        ORDER BY e.event_date ASC
        LIMIT 5
    """)

    recent_registrations = query_db("""
        SELECT p.name AS participant_name, e.event_name, r.registration_date, r.status
        FROM registrations r
        JOIN participants p ON r.participant_id = p.id
        JOIN events e ON r.event_id = e.id
        ORDER BY r.registration_date DESC
        LIMIT 5
    """)

    latest_notices = query_db("""
        SELECT * FROM notices ORDER BY posted_date DESC LIMIT 3
    """)

    return render_template('dashboard.html',
                           total_clubs=total_clubs,
                           total_events=total_events,
                           total_participants=total_participants,
                           total_registrations=total_registrations,
                           upcoming_events=upcoming_events,
                           recent_registrations=recent_registrations,
                           latest_notices=latest_notices)


# ─────────────────────────────────────────────
# CLUBS
# ─────────────────────────────────────────────

@app.route('/clubs')
@login_required
def clubs():
    rows = query_db("""
        SELECT c.*, COUNT(e.id) AS total_events
        FROM clubs c
        LEFT JOIN events e ON c.id = e.club_id
        GROUP BY c.id
        ORDER BY c.club_name
    """)
    return render_template('clubs.html', clubs=rows)


@app.route('/clubs/add', methods=['GET', 'POST'])
@login_required
def add_club():
    if request.method == 'POST':
        club_name = request.form['club_name'].strip()
        description = request.form.get('description', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        email = request.form.get('email', '').strip()
        execute_db(
            'INSERT INTO clubs (club_name, description, contact_person, email) VALUES (%s, %s, %s, %s)',
            (club_name, description, contact_person, email)
        )
        flash('Club added successfully!', 'success')
        return redirect(url_for('clubs'))
    return render_template('add_club.html', club=None)


@app.route('/clubs/<int:club_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_club(club_id):
    club = query_db('SELECT * FROM clubs WHERE id = %s', (club_id,), one=True)
    if not club:
        flash('Club not found.', 'danger')
        return redirect(url_for('clubs'))
    if request.method == 'POST':
        club_name = request.form['club_name'].strip()
        description = request.form.get('description', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        email = request.form.get('email', '').strip()
        execute_db(
            'UPDATE clubs SET club_name=%s, description=%s, contact_person=%s, email=%s WHERE id=%s',
            (club_name, description, contact_person, email, club_id)
        )
        flash('Club updated successfully!', 'success')
        return redirect(url_for('clubs'))
    return render_template('add_club.html', club=club)


@app.route('/clubs/<int:club_id>/delete', methods=['POST'])
@login_required
def delete_club(club_id):
    execute_db('DELETE FROM clubs WHERE id = %s', (club_id,))
    flash('Club deleted successfully.', 'success')
    return redirect(url_for('clubs'))


@app.route('/clubs/<int:club_id>')
@login_required
def club_detail(club_id):
    club = query_db('SELECT * FROM clubs WHERE id = %s', (club_id,), one=True)
    if not club:
        flash('Club not found.', 'danger')
        return redirect(url_for('clubs'))
    events = query_db("""
        SELECT e.*, COUNT(r.id) AS registered_count,
               (e.max_participants - COUNT(r.id)) AS slots_left
        FROM events e
        LEFT JOIN registrations r ON e.id = r.event_id
        WHERE e.club_id = %s
        GROUP BY e.id
        ORDER BY e.event_date DESC
    """, (club_id,))
    return render_template('club_detail.html', club=club, events=events)


# ─────────────────────────────────────────────
# EVENTS
# ─────────────────────────────────────────────

@app.route('/events')
@login_required
def events():
    filter_tab = request.args.get('filter', 'all')
    search = request.args.get('search', '').strip()

    base_sql = """
        SELECT e.id, e.event_name, c.club_name, e.event_date, e.venue,
               e.max_participants, COUNT(r.id) AS registered_count,
               (e.max_participants - COUNT(r.id)) AS slots_left
        FROM events e
        JOIN clubs c ON e.club_id = c.id
        LEFT JOIN registrations r ON e.id = r.event_id
        WHERE 1=1
    """
    params = []

    if filter_tab == 'upcoming':
        base_sql += ' AND e.event_date >= CURDATE()'
    elif filter_tab == 'past':
        base_sql += ' AND e.event_date < CURDATE()'

    if search:
        base_sql += ' AND (e.event_name LIKE %s OR c.club_name LIKE %s)'
        params += [f'%{search}%', f'%{search}%']

    base_sql += ' GROUP BY e.id ORDER BY e.event_date DESC'
    rows = query_db(base_sql, params)
    clubs_list = query_db('SELECT id, club_name FROM clubs ORDER BY club_name')
    return render_template('events.html', events=rows, clubs=clubs_list,
                           filter_tab=filter_tab, search=search)


@app.route('/events/add', methods=['GET', 'POST'])
@login_required
def add_event():
    clubs_list = query_db('SELECT id, club_name FROM clubs ORDER BY club_name')
    if request.method == 'POST':
        club_id = request.form['club_id']
        event_name = request.form['event_name'].strip()
        event_date = request.form['event_date']
        venue = request.form.get('venue', '').strip()
        max_participants = request.form.get('max_participants', 100)
        description = request.form.get('description', '').strip()
        execute_db(
            'INSERT INTO events (club_id, event_name, event_date, venue, max_participants, description) VALUES (%s,%s,%s,%s,%s,%s)',
            (club_id, event_name, event_date, venue, max_participants, description)
        )
        flash('Event added successfully!', 'success')
        return redirect(url_for('events'))
    return render_template('add_event.html', clubs=clubs_list, event=None)


@app.route('/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = query_db('SELECT * FROM events WHERE id = %s', (event_id,), one=True)
    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('events'))
    clubs_list = query_db('SELECT id, club_name FROM clubs ORDER BY club_name')
    if request.method == 'POST':
        club_id = request.form['club_id']
        event_name = request.form['event_name'].strip()
        event_date = request.form['event_date']
        venue = request.form.get('venue', '').strip()
        max_participants = request.form.get('max_participants', 100)
        description = request.form.get('description', '').strip()
        execute_db(
            'UPDATE events SET club_id=%s, event_name=%s, event_date=%s, venue=%s, max_participants=%s, description=%s WHERE id=%s',
            (club_id, event_name, event_date, venue, max_participants, description, event_id)
        )
        flash('Event updated successfully!', 'success')
        return redirect(url_for('events'))
    return render_template('add_event.html', clubs=clubs_list, event=event)


@app.route('/events/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    execute_db('DELETE FROM events WHERE id = %s', (event_id,))
    flash('Event deleted successfully.', 'success')
    return redirect(url_for('events'))


@app.route('/events/<int:event_id>')
@login_required
def event_detail(event_id):
    event = query_db("""
        SELECT e.*, c.club_name,
               COUNT(r.id) AS registered_count,
               (e.max_participants - COUNT(r.id)) AS slots_left
        FROM events e
        JOIN clubs c ON e.club_id = c.id
        LEFT JOIN registrations r ON e.id = r.event_id
        WHERE e.id = %s
        GROUP BY e.id
    """, (event_id,), one=True)
    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('events'))
    registrations = query_db("""
        SELECT r.id, p.name, p.email, p.phone, p.college_branch, p.year,
               r.registration_date, r.status
        FROM registrations r
        JOIN participants p ON r.participant_id = p.id
        WHERE r.event_id = %s
        ORDER BY r.registration_date
    """, (event_id,))
    return render_template('event_detail.html', event=event, registrations=registrations)


@app.route('/events/<int:event_id>/mark_attended/<int:reg_id>', methods=['POST'])
@login_required
def mark_attended(event_id, reg_id):
    execute_db("UPDATE registrations SET status='attended' WHERE id=%s", (reg_id,))
    flash('Marked as attended.', 'success')
    return redirect(url_for('event_detail', event_id=event_id))


@app.route('/events/<int:event_id>/issue_certificate/<int:reg_id>', methods=['POST'])
@login_required
def issue_certificate(event_id, reg_id):
    execute_db("UPDATE registrations SET status='certificate_issued' WHERE id=%s", (reg_id,))
    flash('Certificate issued.', 'success')
    return redirect(url_for('event_detail', event_id=event_id))


@app.route('/events/<int:event_id>/bulk_attended', methods=['POST'])
@login_required
def bulk_attended(event_id):
    execute_db("UPDATE registrations SET status='attended' WHERE event_id=%s AND status='registered'", (event_id,))
    flash('All registered participants marked as attended.', 'success')
    return redirect(url_for('event_detail', event_id=event_id))


@app.route('/events/<int:event_id>/export_csv')
@login_required
def export_csv(event_id):
    event = query_db('SELECT event_name FROM events WHERE id=%s', (event_id,), one=True)
    registrations = query_db("""
        SELECT p.name, p.email, p.phone, p.college_branch, p.year,
               r.registration_date, r.status
        FROM registrations r
        JOIN participants p ON r.participant_id = p.id
        WHERE r.event_id = %s
        ORDER BY r.registration_date
    """, (event_id,))

    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['Name', 'Email', 'Phone', 'Branch', 'Year', 'Registration Date', 'Status'])
    for row in registrations:
        writer.writerow([row['name'], row['email'], row['phone'],
                         row['college_branch'], row['year'],
                         row['registration_date'], row['status']])
    output = make_response(si.getvalue())
    filename = f"{event['event_name'].replace(' ', '_')}_registrations.csv"
    output.headers['Content-Disposition'] = f'attachment; filename={filename}'
    output.headers['Content-type'] = 'text/csv'
    return output


# ─────────────────────────────────────────────
# PARTICIPANTS
# ─────────────────────────────────────────────

@app.route('/participants')
@login_required
def participants():
    search = request.args.get('search', '').strip()
    sql = """
        SELECT p.*, COUNT(r.id) AS total_registrations
        FROM participants p
        LEFT JOIN registrations r ON p.id = r.participant_id
        WHERE 1=1
    """
    params = []
    if search:
        sql += ' AND (p.name LIKE %s OR p.email LIKE %s)'
        params += [f'%{search}%', f'%{search}%']
    sql += ' GROUP BY p.id ORDER BY p.name'
    rows = query_db(sql, params)
    return render_template('participants.html', participants=rows, search=search)


@app.route('/participants/add', methods=['GET', 'POST'])
@login_required
def add_participant():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        phone = request.form.get('phone', '').strip()
        branch = request.form.get('college_branch', '').strip()
        year = request.form.get('year', '').strip()
        execute_db(
            'INSERT INTO participants (name, email, phone, college_branch, year) VALUES (%s,%s,%s,%s,%s)',
            (name, email, phone, branch, year)
        )
        flash('Participant added successfully!', 'success')
        return redirect(url_for('participants'))
    return render_template('add_participant.html')


@app.route('/participants/<int:participant_id>')
@login_required
def participant_detail(participant_id):
    participant = query_db('SELECT * FROM participants WHERE id=%s', (participant_id,), one=True)
    if not participant:
        flash('Participant not found.', 'danger')
        return redirect(url_for('participants'))
    regs = query_db("""
        SELECT r.id, e.event_name, c.club_name, e.event_date, r.registration_date, r.status
        FROM registrations r
        JOIN events e ON r.event_id = e.id
        JOIN clubs c ON e.club_id = c.id
        WHERE r.participant_id = %s
        ORDER BY r.registration_date DESC
    """, (participant_id,))
    return render_template('participant_detail.html', participant=participant, registrations=regs)


@app.route('/participants/<int:participant_id>/delete', methods=['POST'])
@login_required
def delete_participant(participant_id):
    execute_db('DELETE FROM participants WHERE id=%s', (participant_id,))
    flash('Participant deleted.', 'success')
    return redirect(url_for('participants'))


# ─────────────────────────────────────────────
# REGISTRATIONS
# ─────────────────────────────────────────────

@app.route('/registrations')
@login_required
def registrations():
    filter_tab = request.args.get('filter', 'all')
    search = request.args.get('search', '').strip()

    sql = """
        SELECT r.id, p.name AS participant_name, e.event_name, c.club_name,
               r.registration_date, r.status
        FROM registrations r
        JOIN participants p ON r.participant_id = p.id
        JOIN events e ON r.event_id = e.id
        JOIN clubs c ON e.club_id = c.id
        WHERE 1=1
    """
    params = []
    if filter_tab != 'all':
        sql += ' AND r.status = %s'
        params.append(filter_tab)
    if search:
        sql += ' AND (p.name LIKE %s OR e.event_name LIKE %s)'
        params += [f'%{search}%', f'%{search}%']
    sql += ' ORDER BY r.registration_date DESC'
    rows = query_db(sql, params)

    participants_list = query_db('SELECT id, name FROM participants ORDER BY name')
    events_list = query_db('SELECT id, event_name FROM events ORDER BY event_name')

    return render_template('registrations.html', registrations=rows,
                           filter_tab=filter_tab, search=search,
                           participants_list=participants_list,
                           events_list=events_list)


@app.route('/registrations/add', methods=['POST'])
@login_required
def add_registration():
    participant_id = request.form['participant_id']
    event_id = request.form['event_id']
    existing = query_db(
        'SELECT id FROM registrations WHERE participant_id=%s AND event_id=%s',
        (participant_id, event_id), one=True
    )
    if existing:
        flash('Participant is already registered for this event.', 'warning')
    else:
        execute_db(
            "INSERT INTO registrations (event_id, participant_id, status) VALUES (%s,%s,'registered')",
            (event_id, participant_id)
        )
        flash('Registration added successfully!', 'success')
    return redirect(url_for('registrations'))


@app.route('/registrations/<int:reg_id>/update_status', methods=['POST'])
@login_required
def update_registration_status(reg_id):
    new_status = request.form['status']
    if new_status in ('registered', 'attended', 'certificate_issued'):
        execute_db('UPDATE registrations SET status=%s WHERE id=%s', (new_status, reg_id))
        flash('Status updated.', 'success')
    return redirect(url_for('registrations'))


@app.route('/registrations/<int:reg_id>/delete', methods=['POST'])
@login_required
def delete_registration(reg_id):
    execute_db('DELETE FROM registrations WHERE id=%s', (reg_id,))
    flash('Registration deleted.', 'success')
    return redirect(url_for('registrations'))


# ─────────────────────────────────────────────
# NOTICES
# ─────────────────────────────────────────────

@app.route('/notices')
@login_required
def notices():
    rows = query_db('SELECT * FROM notices ORDER BY posted_date DESC')
    return render_template('notices.html', notices=rows)


@app.route('/notices/add', methods=['POST'])
@login_required
def add_notice():
    title = request.form['title'].strip()
    message = request.form['message'].strip()
    execute_db(
        'INSERT INTO notices (title, message, admin_id) VALUES (%s,%s,%s)',
        (title, message, current_user.id)
    )
    flash('Notice posted successfully!', 'success')
    return redirect(url_for('notices'))


@app.route('/notices/<int:notice_id>/delete', methods=['POST'])
@login_required
def delete_notice(notice_id):
    execute_db('DELETE FROM notices WHERE id=%s', (notice_id,))
    flash('Notice deleted.', 'success')
    return redirect(url_for('notices'))


# ─────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            admin = query_db('SELECT * FROM admins WHERE id=%s', (current_user.id,), one=True)
            if not check_password_hash(admin['password_hash'], current_pw):
                flash('Current password is incorrect.', 'danger')
            elif new_pw != confirm_pw:
                flash('New passwords do not match.', 'danger')
            elif len(new_pw) < 6:
                flash('Password must be at least 6 characters.', 'danger')
            else:
                execute_db(
                    'UPDATE admins SET password_hash=%s WHERE id=%s',
                    (generate_password_hash(new_pw), current_user.id)
                )
                flash('Password changed successfully!', 'success')

        elif action == 'update_college':
            college_name = request.form.get('college_name', '').strip()
            existing = query_db("SELECT id FROM settings WHERE `key`='college_name'", one=True)
            if existing:
                execute_db("UPDATE settings SET value=%s WHERE `key`='college_name'", (college_name,))
            else:
                execute_db("INSERT INTO settings (`key`, value) VALUES ('college_name', %s)", (college_name,))
            flash('College name updated!', 'success')

        return redirect(url_for('settings'))

    college_name_row = query_db("SELECT value FROM settings WHERE `key`='college_name'", one=True)
    college_name = college_name_row['value'] if college_name_row else ''
    return render_template('settings.html', college_name=college_name)


# ─────────────────────────────────────────────
# DB INIT (run once via /init-db?token=<SECRET_KEY>)
# ─────────────────────────────────────────────

@app.route('/init-db')
def init_db():
    """
    One-time route to create tables and seed default data on Railway.
    Protected by the SECRET_KEY token so it can't be abused.
    Visit: https://your-app.railway.app/init-db?token=YOUR_SECRET_KEY
    """
    token = request.args.get('token', '')
    if token != app.secret_key:
        return 'Forbidden', 403

    db = get_db()
    cursor = db.cursor()

    statements = [
        """CREATE TABLE IF NOT EXISTS admins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS clubs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            club_name VARCHAR(150) NOT NULL,
            description TEXT,
            contact_person VARCHAR(100),
            email VARCHAR(150),
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            club_id INT NOT NULL,
            event_name VARCHAR(200) NOT NULL,
            event_date DATE NOT NULL,
            venue VARCHAR(200),
            max_participants INT DEFAULT 100,
            description TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (club_id) REFERENCES clubs(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS participants (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL UNIQUE,
            phone VARCHAR(20),
            college_branch VARCHAR(100),
            year VARCHAR(20)
        )""",
        """CREATE TABLE IF NOT EXISTS registrations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            event_id INT NOT NULL,
            participant_id INT NOT NULL,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status ENUM('registered','attended','certificate_issued') DEFAULT 'registered',
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY (participant_id) REFERENCES participants(id) ON DELETE CASCADE,
            UNIQUE KEY unique_reg (event_id, participant_id)
        )""",
        """CREATE TABLE IF NOT EXISTS notices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            message TEXT NOT NULL,
            posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            admin_id INT,
            FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE SET NULL
        )""",
        """CREATE TABLE IF NOT EXISTS settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            `key` VARCHAR(100) NOT NULL UNIQUE,
            value TEXT
        )""",
    ]

    for stmt in statements:
        cursor.execute(stmt)

    # Default settings
    cursor.execute("INSERT IGNORE INTO settings (`key`, value) VALUES ('college_name', 'My College')")

    # Default admin
    cursor.execute("SELECT id FROM admins WHERE email='admin@clubevents.com'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO admins (name, email, password_hash) VALUES (%s, %s, %s)",
            ('Admin', 'admin@clubevents.com', generate_password_hash('admin123'))
        )

    db.commit()
    cursor.close()
    return '''
    <h2 style="font-family:sans-serif;color:green">✅ Database initialised successfully!</h2>
    <p style="font-family:sans-serif">
      Tables created and default admin seeded.<br>
      Login at <a href="/login">/login</a> with
      <code>admin@clubevents.com</code> / <code>admin123</code>
    </p>
    <p style="font-family:sans-serif;color:red">
      ⚠️ Change your password immediately after first login.
    </p>
    '''


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')
