import sqlite3
import os
import json

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'gendutin.db')
SEED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'seed_foods.json')

def get_connection():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # User Profile Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT DEFAULT 'User',
        age INTEGER,
        gender TEXT,
        weight REAL,
        height REAL,
        activity_level TEXT,
        target_weight REAL,
        surplus_kcal INTEGER,
        target_calories REAL,
        target_protein REAL,
        target_carbs REAL,
        target_fat REAL,
        likes_text TEXT DEFAULT '',
        dislikes_text TEXT DEFAULT '',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Safe migration v2: free-form preference columns
    for migration_col in ["likes_text TEXT DEFAULT ''", "dislikes_text TEXT DEFAULT ''"]:
        try:
            cursor.execute(f"ALTER TABLE user_profile ADD COLUMN {migration_col}")
        except Exception:
            pass  # Kolom sudah ada — aman diabaikan

    # Safe migration v3: AI Lifestyle profiling columns
    for migration_col in [
        "activity_description TEXT DEFAULT ''",
        "activity_multiplier REAL DEFAULT 0.0",
    ]:
        try:
            cursor.execute(f"ALTER TABLE user_profile ADD COLUMN {migration_col}")
        except Exception:
            pass  # Kolom sudah ada — aman diabaikan
    
    # Foods Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS foods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        calories REAL,
        protein REAL,
        carbs REAL,
        fat REAL,
        category TEXT,
        is_liked INTEGER DEFAULT 0, -- 1: Liked, -1: Disliked, 0: Neutral
        is_custom INTEGER DEFAULT 0
    )
    ''')
    
    # Daily Logs Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, -- YYYY-MM-DD
        food_id INTEGER,
        quantity REAL, -- multiplier or serving factor
        calories REAL,
        protein REAL,
        carbs REAL,
        fat REAL,
        FOREIGN KEY (food_id) REFERENCES foods(id)
    )
    ''')
    
    # Weight Logs Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS weight_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE, -- YYYY-MM-DD
        weight REAL
    )
    ''')
    
    # Recipes Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        ingredients TEXT, -- JSON array of ingredient names
        instructions TEXT,
        calories REAL,
        protein REAL,
        carbs REAL,
        fat REAL
    )
    ''')
    
    conn.commit()
    conn.close()
    
    seed_database()

def seed_database():
    if not os.path.exists(SEED_FILE):
        return
        
    with open(SEED_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # Seed Foods
    for food in data.get('foods', []):
        try:
            cursor.execute('''
            INSERT OR IGNORE INTO foods (name, calories, protein, carbs, fat, category, is_liked)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (food['name'], food['calories'], food['protein'], food['carbs'], food['fat'], food['category'], 0))
        except Exception as e:
            print(f"Error seeding food {food['name']}: {e}")
            
    # Seed Recipes
    for recipe in data.get('recipes', []):
        try:
            cursor.execute('''
            INSERT OR IGNORE INTO recipes (name, ingredients, instructions, calories, protein, carbs, fat)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                recipe['name'], 
                json.dumps(recipe['ingredients']), 
                recipe['instructions'], 
                recipe['calories'], 
                recipe['protein'], 
                recipe['carbs'], 
                recipe['fat']
            ))
        except Exception as e:
            print(f"Error seeding recipe {recipe['name']}: {e}")
            
    conn.commit()
    conn.close()

# User profile helper functions
def get_user_profile():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_profile ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def save_user_profile(profile_data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO user_profile (
        name, age, gender, weight, height, activity_level, target_weight,
        surplus_kcal, target_calories, target_protein, target_carbs, target_fat,
        likes_text, dislikes_text, activity_description, activity_multiplier
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        profile_data.get('name', 'User'),
        profile_data['age'],
        profile_data['gender'],
        profile_data['weight'],
        profile_data['height'],
        profile_data['activity_level'],
        profile_data['target_weight'],
        profile_data['surplus_kcal'],
        profile_data['target_calories'],
        profile_data['target_protein'],
        profile_data['target_carbs'],
        profile_data['target_fat'],
        profile_data.get('likes_text', ''),
        profile_data.get('dislikes_text', ''),
        profile_data.get('activity_description', ''),
        profile_data.get('activity_multiplier', 0.0),
    ))
    conn.commit()
    conn.close()

# Food helper functions
def get_all_foods(search="", show_preference=None):
    """
    show_preference: 1 (Liked only), -1 (Disliked only), 0 (Neutral only), None (All except Disliked unless specified)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM foods WHERE name LIKE ?"
    params = [f"%{search}%"]
    
    if show_preference is not None:
        query += " AND is_liked = ?"
        params.append(show_preference)
    else:
        # Default behavior: show everything except disliked (is_liked != -1)
        query += " AND is_liked != -1"
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_food_preference(food_id, is_liked):
    """
    is_liked: 1 (Liked), -1 (Disliked), 0 (Neutral)
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE foods SET is_liked = ? WHERE id = ?", (is_liked, food_id))
    conn.commit()
    conn.close()

def add_custom_food(name, calories, protein, carbs, fat, category):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO foods (name, calories, protein, carbs, fat, category, is_custom)
        VALUES (?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(name) DO UPDATE SET
            calories = excluded.calories,
            protein = excluded.protein,
            carbs = excluded.carbs,
            fat = excluded.fat,
            category = excluded.category,
            is_custom = 1
        ''', (name, calories, protein, carbs, fat, category))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

# Daily logs helper functions
def log_food_consumption(date_str, food_id, quantity):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT calories, protein, carbs, fat FROM foods WHERE id = ?", (food_id,))
    food = cursor.fetchone()
    if not food:
        conn.close()
        return False
        
    factor = quantity
    cal = food['calories'] * factor
    prot = food['protein'] * factor
    carb = food['carbs'] * factor
    fat = food['fat'] * factor
    
    cursor.execute('''
    INSERT INTO daily_logs (date, food_id, quantity, calories, protein, carbs, fat)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (date_str, food_id, quantity, cal, prot, carb, fat))
    conn.commit()
    conn.close()
    return True

def get_daily_logs(date_str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT dl.*, f.name as food_name, f.category as food_category 
    FROM daily_logs dl
    JOIN foods f ON dl.food_id = f.id
    WHERE dl.date = ?
    ''', (date_str,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_daily_log(log_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM daily_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()

# Weight logs helper functions
def log_weight(date_str, weight):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO weight_logs (date, weight)
    VALUES (?, ?)
    ON CONFLICT(date) DO UPDATE SET weight = excluded.weight
    ''', (date_str, weight))
    conn.commit()
    conn.close()
    
    # Update latest user profile with the new weight and recalculated targets
    profile = get_user_profile()
    if profile:
        import engine
        multiplier = profile.get("activity_multiplier", 0.0)
        if multiplier and multiplier > 0:
            macros = engine.hitung_target_makro_dari_multiplier(
                weight,
                profile["height"],
                profile["age"],
                profile["gender"],
                multiplier
            )
        else:
            macros = engine.hitung_target_makro(
                weight,
                profile["height"],
                profile["age"],
                profile["gender"],
                profile.get("activity_level", "Moderately Active")
            )
            
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE user_profile
        SET weight = ?,
            target_calories = ?,
            target_protein = ?,
            target_carbs = ?,
            target_fat = ?
        WHERE id = ?
        ''', (
            weight,
            macros["target_calories"],
            macros["target_protein"],
            macros["target_carbs"],
            macros["target_fat"],
            profile["id"]
        ))
        conn.commit()
        conn.close()

def get_weight_logs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM weight_logs ORDER BY date ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Recipes helper functions
def get_all_recipes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipes")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
