"""
Run this script ONCE after schema.sql to create the default admin account.
Usage: python seed_admin.py
"""
import os
from werkzeug.security import generate_password_hash
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

conn = mysql.connector.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'club_events_db')
)
cursor = conn.cursor()

email = 'admin@clubevents.com'
password = 'admin123'
name = 'Admin'

cursor.execute('SELECT id FROM admins WHERE email = %s', (email,))
existing = cursor.fetchone()

if existing:
    cursor.execute(
        'UPDATE admins SET password_hash=%s, name=%s WHERE email=%s',
        (generate_password_hash(password), name, email)
    )
    print(f'Admin updated: {email}')
else:
    cursor.execute(
        'INSERT INTO admins (name, email, password_hash) VALUES (%s, %s, %s)',
        (name, email, generate_password_hash(password))
    )
    print(f'Admin created: {email}')

conn.commit()
cursor.close()
conn.close()
print('Done. Login with admin@clubevents.com / admin123')
