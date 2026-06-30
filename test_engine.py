import unittest
from engine import hitung_target_makro, cocokan_resep_berbasis_bahan

class TestGendutinEngine(unittest.TestCase):
    def test_hitung_target_makro_pria(self):
        # Data uji pria
        berat = 70.0       # kg
        tinggi = 175.0     # cm
        umur = 25          # tahun
        gender = 'Pria'
        tingkat_aktivitas = 'Moderately Active'  # multiplier 1.55
        
        # Perhitungan Manual:
        # BMR = 10 * 70 + 6.25 * 175 - 5 * 25 + 5
        #     = 700 + 1093.75 - 125 + 5 = 1673.75
        # TDEE = 1673.75 * 1.55 = 2594.3125 (dibulatkan di fungsi)
        # Target Calories = 2594.3125 + 400 = 2994.3125 -> 2994.31
        # Target Protein = 2 * 70 = 140.0 g (560 kkal)
        # Target Fat = 2994.3125 * 0.25 / 9 = 748.578125 / 9 = 83.175 -> 83.18 g
        # Target Carbs = (2994.3125 - 560 - 748.578125) / 4 = 1685.734375 / 4 = 421.4335 -> 421.43 g
        
        hasil = hitung_target_makro(berat, tinggi, umur, gender, tingkat_aktivitas)
        
        self.assertAlmostEqual(hasil['bmr'], 1673.75, places=2)
        self.assertAlmostEqual(hasil['tdee'], 2594.31, places=1)
        self.assertAlmostEqual(hasil['target_calories'], 2994.31, places=1)
        self.assertAlmostEqual(hasil['target_protein'], 140.0, places=2)
        self.assertAlmostEqual(hasil['target_fat'], 83.18, places=1)
        self.assertAlmostEqual(hasil['target_carbs'], 421.43, places=1)

    def test_hitung_target_makro_wanita(self):
        # Data uji wanita
        berat = 50.0
        tinggi = 160.0
        umur = 30
        gender = 'Wanita'
        tingkat_aktivitas = 'Sedentary'  # multiplier 1.2
        
        # Perhitungan Manual:
        # BMR = 10 * 50 + 6.25 * 160 - 5 * 30 - 161
        #     = 500 + 1000 - 150 - 161 = 1189.0
        # TDEE = 1189.0 * 1.2 = 1426.8
        # Target Calories = 1426.8 + 400 = 1826.8
        # Target Protein = 2 * 50 = 100.0 g (400 kkal)
        # Target Fat = 1826.8 * 0.25 / 9 = 456.7 / 9 = 50.74 g
        # Target Carbs = (1826.8 - 400 - 456.7) / 4 = 970.1 / 4 = 242.525 g
        
        hasil = hitung_target_makro(berat, tinggi, umur, gender, tingkat_aktivitas)
        
        self.assertAlmostEqual(hasil['bmr'], 1189.0, places=2)
        self.assertAlmostEqual(hasil['tdee'], 1426.8, places=2)
        self.assertAlmostEqual(hasil['target_calories'], 1826.8, places=2)
        self.assertAlmostEqual(hasil['target_protein'], 100.0, places=2)
        self.assertAlmostEqual(hasil['target_fat'], 50.74, places=1)
        self.assertAlmostEqual(hasil['target_carbs'], 242.53, places=1)

    def test_cocokan_resep_berbasis_bahan(self):
        # Mock database resep
        resep_db = [
            {
                "name": "Bulking Oatmeal Surprise",
                "ingredients": ["Oats / Havermut (1 Mangkuk / 50g)", "Susu Sapi Full Cream (1 Gelas / 250ml)", "Selai Kacang (2 Sendok Makan / 32g)"],
                "calories": 528
            },
            {
                "name": "Telur Rebus Praktis",
                "ingredients": ["Telur Rebus (1 Butir Besar)", "Garam"],
                "calories": 80
            }
        ]
        
        # Test mencocokkan bahan 'oats' dan 'susu'
        bahan_user = ["oats", "susu"]
        hasil = cocokan_resep_berbasis_bahan(bahan_user, resep_db)
        
        # Harus mencocokkan "Bulking Oatmeal Surprise" karena ada Oats dan Susu
        self.assertTrue(len(hasil) > 0)
        self.assertEqual(hasil[0]['name'], "Bulking Oatmeal Surprise")
        self.assertEqual(hasil[0]['match_count'], 2)
        self.assertEqual(hasil[0]['total_count'], 3)
        self.assertAlmostEqual(hasil[0]['match_percentage'], 66.67, places=2)

if __name__ == '__main__':
    unittest.main()
