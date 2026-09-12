from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import os
from dotenv import load_dotenv

# Membaca file .env jika ada di lokal
load_dotenv()

app = Flask(__name__)


# =========================
# KONEKSI DATABASE
# =========================
def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQLHOST", "localhost"),
        user=os.getenv("MYSQLUSER", "root"),
        password=os.getenv("MYSQLPASSWORD", ""),
        database=os.getenv("MYSQLDATABASE", "railway"),  # Menggunakan default database 'railway'
        port=int(os.getenv("MYSQLPORT", 3306))
    )


# =========================
# OTOMATIS BUAT DATABASE & TABEL
# =========================
def init_db():
    try:
        # 1. Koneksi awal tanpa nama database untuk memastikan database terbentuk
        conn = mysql.connector.connect(
            host=os.getenv("MYSQLHOST", "localhost"),
            user=os.getenv("MYSQLUSER", "root"),
            password=os.getenv("MYSQLPASSWORD", ""),
            port=int(os.getenv("MYSQLPORT", 3306))
        )
        cursor_init = conn.cursor()
        db_name = os.getenv("MYSQLDATABASE", "railway")
        cursor_init.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        cursor_init.close()
        conn.close()

        # 2. Koneksi ke database yang sudah dipastikan ada
        db = get_db()
        cursor = db.cursor()

        # Buat tabel users jika belum ada
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user'
            );
        """)

        # Buat tabel bookings jika belum ada
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nama VARCHAR(100) NOT NULL,
                whatsapp VARCHAR(20) NOT NULL,
                tanggal DATE NOT NULL,
                jumlah INT NOT NULL,
                anggota TEXT,
                total INT NOT NULL,
                status VARCHAR(50) DEFAULT 'Menunggu Pembayaran'
            );
        """)

        # Buat akun admin default jika belum ada
        cursor.execute("SELECT * FROM users WHERE username = %s", ("admin",))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                ("admin", "admin123", "admin")
            )

        db.commit()
        cursor.close()
        db.close()
        print("Inisialisasi database dan tabel berhasil!")
    except Exception as e:
        print("Gagal inisialisasi database:", e)


# Jalankan pembuatan database & tabel saat aplikasi dimulai
init_db()


# =========================
# LOGIN
# =========================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (username, password)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user:
            if user["role"] == "admin":
                return redirect(url_for("admin"))

            return redirect(url_for("home"))

        return "Username atau password salah! <a href='/'>Kembali</a>"

    return render_template("login.html")


# =========================
# REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username = %s",
            (username,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            cursor.close()
            db.close()
            return "Username sudah digunakan! <a href='/register'>Kembali</a>"

        cursor.execute(
            """
            INSERT INTO users (username, password, role)
            VALUES (%s, %s, 'user')
            """,
            (username, password)
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# =========================
# HALAMAN UTAMA
# =========================
@app.route("/home")
def home():
    return render_template("index.html")


# =========================
# BOOKING
# =========================
@app.route("/booking", methods=["GET", "POST"])
def booking():
    if request.method == "POST":
        nama = request.form["nama"]
        whatsapp = request.form["whatsapp"]
        tanggal = request.form["tanggal"]
        jumlah = int(request.form["jumlah"])
        anggota = request.form["anggota"]

        harga_per_orang = 50000
        total = jumlah * harga_per_orang

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO bookings
            (nama, whatsapp, tanggal, jumlah, anggota, total, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                nama,
                whatsapp,
                tanggal,
                jumlah,
                anggota,
                total,
                "Menunggu Pembayaran"
            )
        )

        db.commit()

        booking_id = cursor.lastrowid

        cursor.close()
        db.close()

        return redirect(url_for(
            "pembayaran",
            id=booking_id
        ))

    return render_template("booking.html")


# =========================
# PEMBAYARAN
# =========================
@app.route("/pembayaran")
def pembayaran():
    booking_id = request.args.get("id")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM bookings WHERE id = %s",
        (booking_id,)
    )

    booking_data = cursor.fetchone()

    cursor.close()
    db.close()

    if not booking_data:
        return "Booking tidak ditemukan!"

    return render_template(
        "pembayaran.html",
        booking=booking_data
    )


# =========================
# SUDAH MEMBAYAR
# =========================
@app.route("/sudah-membayar/<int:id>")
def sudah_membayar(id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE bookings
        SET status = 'Menunggu Konfirmasi Admin'
        WHERE id = %s
        """,
        (id,)
    )

    db.commit()

    cursor.close()
    db.close()

    return redirect(url_for(
        "status",
        id=id
    ))


# =========================
# STATUS BOOKING
# =========================
@app.route("/status")
def status():
    booking_id = request.args.get("id")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM bookings WHERE id = %s",
        (booking_id,)
    )

    booking_data = cursor.fetchone()

    cursor.close()
    db.close()

    if not booking_data:
        return "Booking tidak ditemukan!"

    return render_template(
        "status.html",
        booking=booking_data
    )


# =========================
# ADMIN
# =========================
@app.route("/admin")
def admin():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM bookings ORDER BY id DESC"
    )

    bookings = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin.html",
        bookings=bookings
    )


# =========================
# KONFIRMASI ADMIN
# =========================
@app.route("/admin/konfirmasi/<int:id>")
def konfirmasi(id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE bookings
        SET status = 'Booking Berhasil'
        WHERE id = %s
        """,
        (id,)
    )

    db.commit()

    cursor.close()
    db.close()

    return redirect(url_for("admin"))


# =========================
# JALANKAN FLASK
# =========================
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)