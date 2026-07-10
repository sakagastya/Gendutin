import os
import json
import streamlit as st

SEED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'seed_foods.json')

# Load seed data
_DEFAULT_FOODS = []
_DEFAULT_RECIPES = []
try:
    if os.path.exists(SEED_FILE):
        with open(SEED_FILE, 'r', encoding='utf-8') as f:
            _seed_data = json.load(f)
            _DEFAULT_FOODS = _seed_data.get('foods', [])
            _DEFAULT_RECIPES = _seed_data.get('recipes', [])
            # Assign fake integer IDs for default foods and recipes
            for idx, item in enumerate(_DEFAULT_FOODS, 1):
                item['id'] = idx
            for idx, item in enumerate(_DEFAULT_RECIPES, 1):
                item['id'] = idx
except Exception as e:
    print("Error loading seed foods:", e)

def init_db():
    # Database initialization is now handled in-memory / browser local storage.
    pass

# User profile helper functions
def get_user_profile():
    return st.session_state.get("db_profile")

def save_user_profile(profile_data):
    st.session_state.db_profile = profile_data
    st.session_state.ls_pending_profile = profile_data

# Food helper functions
def get_food_by_id(food_id):
    # Search default foods
    for f in _DEFAULT_FOODS:
        if f["id"] == food_id:
            return f
    # Search custom foods
    custom_foods = st.session_state.get("db_custom_foods", [])
    for f in custom_foods:
        if f["id"] == food_id:
            return f
    return None

def get_all_foods(search="", show_preference=None):
    # Combine default foods and custom foods
    all_items = []
    
    # 1. Add default foods with preferences
    for f in _DEFAULT_FOODS:
        prefs = st.session_state.get("db_food_preferences", {})
        is_liked = prefs.get(f["name"], 0)
        all_items.append({**f, "is_liked": is_liked})
        
    # 2. Add custom foods with preferences
    custom_foods = st.session_state.get("db_custom_foods", [])
    for f in custom_foods:
        prefs = st.session_state.get("db_food_preferences", {})
        is_liked = prefs.get(f["name"], 0)
        all_items.append({**f, "is_liked": is_liked})
        
    # 3. Filter by search query
    filtered = []
    for f in all_items:
        if search.lower() in f["name"].lower():
            if show_preference is not None:
                if f["is_liked"] == show_preference:
                    filtered.append(f)
            else:
                # Default behavior: show everything except disliked (is_liked != -1)
                if f["is_liked"] != -1:
                    filtered.append(f)
                    
    return filtered

def update_food_preference(food_id, is_liked):
    food = get_food_by_id(food_id)
    if food:
        prefs = st.session_state.get("db_food_preferences", {})
        prefs[food["name"]] = is_liked
        st.session_state.db_food_preferences = prefs
        st.session_state.ls_pending_food_prefs = prefs

def add_custom_food(name, calories, protein, carbs, fat, category):
    custom_foods = st.session_state.get("db_custom_foods", [])
    
    # Check duplicate name for upsert behavior
    for f in custom_foods:
        if f["name"].lower() == name.lower():
            f["calories"] = calories
            f["protein"] = protein
            f["carbs"] = carbs
            f["fat"] = fat
            f["category"] = category
            st.session_state.db_custom_foods = custom_foods
            st.session_state.ls_pending_custom_foods = custom_foods
            return True
            
    # Add new
    new_id = 10000 + len(custom_foods) + 1
    new_food = {
        "id": new_id,
        "name": name,
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "category": category,
        "is_liked": 0,
        "is_custom": 1
    }
    custom_foods.append(new_food)
    st.session_state.db_custom_foods = custom_foods
    st.session_state.ls_pending_custom_foods = custom_foods
    return True

# Daily logs helper functions
def log_food_consumption(date_str, food_id, quantity):
    food = get_food_by_id(food_id)
    if not food:
        return False
        
    cal = food['calories'] * quantity
    prot = food['protein'] * quantity
    carb = food['carbs'] * quantity
    fat = food['fat'] * quantity
    
    logs = st.session_state.get("db_daily_logs", [])
    log_id = len(logs) + 1
    new_entry = {
        "id": log_id,
        "date": date_str,
        "food_id": food_id,
        "food_name": food["name"],
        "quantity": quantity,
        "calories": cal,
        "protein": prot,
        "carbs": carb,
        "fat": fat
    }
    logs.append(new_entry)
    st.session_state.db_daily_logs = logs
    st.session_state.ls_pending_daily_logs = logs
    return True

def get_daily_logs(date_str):
    logs = st.session_state.get("db_daily_logs", [])
    result = []
    for l in logs:
        if l["date"] == date_str:
            result.append(l)
    return result

def delete_daily_log(log_id):
    logs = st.session_state.get("db_daily_logs", [])
    logs = [l for l in logs if l["id"] != log_id]
    st.session_state.db_daily_logs = logs
    st.session_state.ls_pending_daily_logs = logs

# Weight logs helper functions
def log_weight(date_str, weight):
    wlogs = st.session_state.get("db_weight_logs", [])
    updated = False
    for wl in wlogs:
        if wl["date"] == date_str:
            wl["weight"] = weight
            updated = True
            break
    if not updated:
        wlogs.append({"date": date_str, "weight": weight})
    wlogs.sort(key=lambda x: x["date"])
    st.session_state.db_weight_logs = wlogs
    st.session_state.ls_pending_weight_logs = wlogs
    
    # Update user profile weight and recalculate targets
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
            
        profile.update({
            "weight": weight,
            "target_calories": macros["target_calories"],
            "target_protein": macros["target_protein"],
            "target_carbs": macros["target_carbs"],
            "target_fat": macros["target_fat"]
        })
        save_user_profile(profile)

def get_weight_logs():
    return st.session_state.get("db_weight_logs", [])

# Recipes helper functions
def get_all_recipes():
    return _DEFAULT_RECIPES
