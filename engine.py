def hitung_target_makro(berat, tinggi, umur, gender, tingkat_aktivitas):
    """
    Menghitung BMR, TDEE, surplus kalori bulking sehat (+400 kkal), 
    dan pembagian makronutrisi harian.
    
    Parameter:
    - berat (float): Berat badan dalam kg.
    - tinggi (float): Tinggi badan dalam cm.
    - umur (int): Umur dalam tahun.
    - gender (str): 'Pria' atau 'Wanita'.
    - tingkat_aktivitas (str): Tingkat aktivitas harian.
      Pilihan: 'Sedentary', 'Lightly Active', 'Moderately Active', 'Very Active', 'Extra Active'.
      
    Kembali:
    - dict: Nilai bmr, tdee, target_calories, target_protein, target_carbs, target_fat.
    """
    # 1. Hitung BMR menggunakan formula Mifflin-St Jeor
    if gender.lower() in ['pria', 'male', 'l']:
        bmr = 10 * berat + 6.25 * tinggi - 5 * umur + 5
    else:
        bmr = 10 * berat + 6.25 * tinggi - 5 * umur - 161

    # 2. Tentukan multiplier aktivitas harian
    multipliers = {
        'Sedentary': 1.2,
        'Lightly Active': 1.375,
        'Moderately Active': 1.55,
        'Very Active': 1.725,
        'Extra Active': 1.9
    }
    
    # Ambil multiplier, default ke Sedentary jika input tidak valid
    multiplier = multipliers.get(tingkat_aktivitas, 1.2)
    tdee = bmr * multiplier

    # 3. Hitung target kalori dengan surplus bulking sehat (+400 kkal)
    surplus = 400
    target_calories = tdee + surplus

    # 4. Hitung pembagian makronutrisi (Target protein disetel ke 2g/kg berat badan)
    # Protein: 2 gram per kg berat badan (1g Protein = 4 kkal)
    target_protein = 2.0 * berat
    protein_calories = target_protein * 4.0

    # Lemak: Disetel ke 25% dari total kalori target (1g Lemak = 9 kkal)
    fat_calories = target_calories * 0.25
    target_fat = fat_calories / 9.0

    # Karbohidrat: Sisa kalori setelah dikurangi protein dan lemak (1g Karbohidrat = 4 kkal)
    remaining_calories = target_calories - (protein_calories + fat_calories)
    # Jika sisa kalori negatif (tidak mungkin dalam surplus sehat, tapi untuk safety), set minimal 0
    target_carbs = max(0.0, remaining_calories / 4.0)

    return {
        'bmr': round(bmr, 2),
        'tdee': round(tdee, 2),
        'target_calories': round(target_calories, 2),
        'target_protein': round(target_protein, 2),
        'target_carbs': round(target_carbs, 2),
        'target_fat': round(target_fat, 2)
    }

def hitung_target_makro_dari_multiplier(berat, tinggi, umur, gender, multiplier):
    """
    Menghitung target makro menggunakan raw multiplier float dari AI Lifestyle Profiler.
    Digunakan ketika user mendeskripsikan aktivitasnya dalam teks bebas dan
    Gemini mengekstrak multiplier TDEE yang paling akurat.

    Parameter:
    - berat (float)     : Berat badan dalam kg.
    - tinggi (float)    : Tinggi badan dalam cm.
    - umur (int)        : Umur dalam tahun.
    - gender (str)      : 'Pria' atau 'Wanita'.
    - multiplier (float): Multiplier aktivitas TDEE (rentang aman: 1.2 – 1.9).

    Kembali:
    - dict: bmr, tdee, target_calories, target_protein, target_carbs, target_fat, multiplier.
    """
    # 1. Hitung BMR menggunakan formula Mifflin-St Jeor
    if gender.lower() in ['pria', 'male', 'l']:
        bmr = 10 * berat + 6.25 * tinggi - 5 * umur + 5
    else:
        bmr = 10 * berat + 6.25 * tinggi - 5 * umur - 161

    # 2. Clamp multiplier ke batas aman agar tidak ada nilai ekstrem
    multiplier = max(1.2, min(2.5, float(multiplier)))
    tdee = bmr * multiplier

    # 3. Surplus bulking sehat +400 kkal
    surplus = 400
    target_calories = tdee + surplus

    # 4. Makronutrisi (logika identik dengan hitung_target_makro)
    target_protein   = 2.0 * berat                           # 2g/kg
    protein_calories = target_protein * 4.0
    fat_calories     = target_calories * 0.25                # 25% total kalori
    target_fat       = fat_calories / 9.0
    remaining_calories = target_calories - (protein_calories + fat_calories)
    target_carbs     = max(0.0, remaining_calories / 4.0)

    return {
        'bmr':             round(bmr, 2),
        'tdee':            round(tdee, 2),
        'target_calories': round(target_calories, 2),
        'target_protein':  round(target_protein, 2),
        'target_carbs':    round(target_carbs, 2),
        'target_fat':      round(target_fat, 2),
        'multiplier':      round(multiplier, 3),
    }


def cocokan_resep_berbasis_bahan(bahan_sekitar, daftar_resep):
    """
    Mencocokkan bahan makanan sekitar dengan database resep.
    Mengembalikan daftar resep yang mengandung salah satu atau lebih bahan input.
    
    Parameter:
    - bahan_sekitar (list of str): List bahan yang dimiliki pengguna.
    - daftar_resep (list of dict): List resep dari database.
    
    Kembali:
    - list of dict: Resep yang cocok beserta tingkat kecocokannya.
    """
    cocok = []
    
    # Normalisasi input bahan
    input_normalized = [b.lower().strip() for b in bahan_sekitar]
    
    for resep in daftar_resep:
        # Resep dari DB menyimpan ingredients sebagai JSON string atau list
        import json
        if isinstance(resep['ingredients'], str):
            try:
                recipe_ingredients = json.loads(resep['ingredients'])
            except:
                recipe_ingredients = []
        else:
            recipe_ingredients = resep['ingredients']
            
        recipe_ingredients_normalized = [i.lower() for i in recipe_ingredients]
        
        # Hitung berapa banyak bahan resep yang cocok dengan bahan sekitar
        matched_ingredients = []
        for ri in recipe_ingredients_normalized:
            for inp in input_normalized:
                if inp in ri:  # partial matching, e.g. "telur" matches "telur rebus"
                    matched_ingredients.append(ri)
                    break
        
        match_count = len(matched_ingredients)
        total_count = len(recipe_ingredients)
        
        if match_count > 0:
            resep_copy = dict(resep)
            resep_copy['match_count'] = match_count
            resep_copy['total_count'] = total_count
            resep_copy['match_percentage'] = round((match_count / total_count) * 100, 2)
            resep_copy['matched_ingredients_list'] = matched_ingredients
            cocok.append(resep_copy)
            
    # Urutkan berdasarkan persentase kecocokan tertinggi
    cocok.sort(key=lambda x: x['match_percentage'], reverse=True)
    return cocok
