import sqlite3
import datetime
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'gendutin.db')

def check_today_logs():
    today = datetime.date.today().strftime('%Y-%m-%d')
    if not os.path.exists(DB_FILE):
        print("🚨 DATABASE ERROR: Database Gendutin belum diinisialisasi!")
        return
        
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Periksa profil aktif
    cursor.execute("SELECT name FROM user_profile ORDER BY id DESC LIMIT 1")
    user = cursor.fetchone()
    user_name = user['name'] if user else "User"
    
    # Hitung jumlah makanan yang dicatat hari ini
    cursor.execute("SELECT COUNT(*) as count FROM daily_logs WHERE date = ?", (today,))
    food_count = cursor.fetchone()['count']
    
    # Hitung berat badan yang dicatat hari ini
    cursor.execute("SELECT COUNT(*) as count FROM weight_logs WHERE date = ?", (today,))
    weight_count = cursor.fetchone()['count']
    
    conn.close()
    
    print("=" * 60)
    print(f"🕵️‍♂️ EVALUASI HARIAN BULKING UNTUK: {user_name.upper()} ({today})")
    print("=" * 60)
    
    alerts = []
    if food_count == 0:
        alerts.append("- 🍕 Anda BELUM mencatat makanan harian hari ini!")
    else:
        print(f"✅ Anda telah mencatat {food_count} makanan hari ini.")
        
    if weight_count == 0:
        alerts.append("- ⚖️ Anda BELUM mencatat berat badan harian hari ini!")
    else:
        print("✅ Anda telah mencatat berat badan hari ini.")
        
    if alerts:
        print("\n🚨 PENGINGAT BULKING BERKALA:")
        for alert in alerts:
            print(alert)
        print("\n👉 Konsistensi surplus kalori dan pelacakan berat badan harian adalah kunci utama keberhasilan bulking Anda! Buka aplikasi Gendutin sekarang untuk mengisi log harian.")
    else:
        print("\n🎉 LUAR BIASA! Semua log harian Anda hari ini lengkap. Pertahankan surplus kalori Anda dan teruskan perjuangan bulking sehat!")
    print("=" * 60)

if __name__ == '__main__':
    check_today_logs()
