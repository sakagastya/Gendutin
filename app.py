# app.py — Gendutin v3: AI-Driven Mobile-First Architecture
# 3-tab navigation | Gemini-only food entry | Daily/Weekly/Monthly insights | AI lifestyle profiling

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime
import database
import engine
import ai_client

st.set_page_config(
    page_title="Gendutin – AI Bulking Tracker",
    page_icon="🏋️",
    layout="centered",
)

try:
    database.init_db()
except Exception as _db_err:
    st.error(
        f"⚠️ Database initialization failed: {_db_err}. "
        "Please reload the page. If the issue persists, contact the developer."
    )
    st.stop()  # Safe — st.stop() here is BEFORE any tab is rendered.


# ── PWA: Mobile Web App Manifest ──────────────────────────────────────────────
# Memungkinkan "Add to Home Screen" di iOS Safari dan Android Chrome.
# Manifest di-embed sebagai data URI — berfungsi di Streamlit Cloud tanpa
# static file hosting terpisah. Meta tags di-inject via st.markdown ke DOM.
import json as _json
import base64 as _b64

_PWA_MANIFEST = {
    "name":             "Gendutin – AI Bulking Tracker",
    "short_name":       "Gendutin",
    "description":      "AI-powered weight gain & macro tracker. Powered by Gemini 2.5 Flash.",
    "start_url":        "/",
    "display":          "standalone",
    "orientation":      "portrait-primary",
    "background_color": "#0F172A",
    "theme_color":      "#3B7DD8",
    "icons": [
        {
            "src":   "https://img.icons8.com/fluency/192/weightlifter.png",
            "sizes": "192x192",
            "type":  "image/png",
        },
        {
            "src":     "https://img.icons8.com/fluency/512/weightlifter.png",
            "sizes":   "512x512",
            "type":    "image/png",
            "purpose": "maskable any",
        },
    ],
}
_manifest_b64 = _b64.b64encode(_json.dumps(_PWA_MANIFEST).encode()).decode()

st.markdown(f"""
<link rel="manifest" href="data:application/manifest+json;base64,{_manifest_b64}">
<meta name="mobile-web-app-capable"                content="yes">
<meta name="apple-mobile-web-app-capable"          content="yes">
<meta name="apple-mobile-web-app-title"            content="Gendutin">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color"                           content="#3B7DD8">
<meta name="description"
      content="AI-powered weight gain macro tracker powered by Gemini 2.5 Flash.">
""", unsafe_allow_html=True)


# ── Helper: reusable macro bar chart (defined before tabs to avoid NameError) ─
def _plot_macro_bar(targets, consumed, labels):
    """Renders a clean, theme-transparent grouped bar chart for macro comparison."""
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(5, 3))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    x = range(len(labels))
    w = 0.36
    ax.bar([i - w / 2 for i in x], targets,  w, color="#94A3B8", alpha=0.85, label="Target")
    ax.bar([i + w / 2 for i in x], consumed, w, color="#3B7DD8", alpha=0.92, label="Dikonsumsi")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.tick_params(axis="y", labelsize=8)
    ax.legend(frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    st.pyplot(fig)


# ── Session state ─────────────────────────────────────────────────────
_SS_DEFAULTS = {"ai_preview": None, "ai_activity_result": None, "user_gemini_key": ""}
for k, v in _SS_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

profile   = database.get_user_profile()
_user_key = st.session_state.user_gemini_key
status    = ai_client.api_status(_user_key)

# ── Compact header ─────────────────────────────────────────────────────
h1, h2 = st.columns([4, 1])
h1.markdown("## 🏋️ Gendutin")
if status["configured"]:
    h2.success("AI ✅")
else:
    h2.warning("🔑 ⚠️")
st.caption("AI-Powered Bulking Tracker · Gemini 2.5 Flash")
st.divider()

# ── 3-Tab mobile navigation ───────────────────────────────────────────────────
tab_insights, tab_quicklog, tab_setup = st.tabs([
    "📊 Insights", "🍕 Quick Log", "👤 Lifestyle Setup"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: INSIGHTS — Daily / Weekly / Monthly
# ══════════════════════════════════════════════════════════════════════════════
with tab_insights:
    if not profile:
        # ── Welcome state: fresh cloud container, no profile yet ───────────────
        with st.container(border=True):
            st.markdown("### 👋 Selamat datang di Gendutin!")
            st.write(
                "Sepertinya ini pertama kali Anda menggunakan app ini. "
                "Buka tab **👤 Lifestyle Setup** untuk mengisi data fisik dan "
                "gaya hidup Anda — Gemini akan menghitung target kalori secara otomatis."
            )
            st.info(
                "💡 Setelah profil tersimpan, kembali ke tab ini untuk melihat "
                "grafik progres **Harian**, **Mingguan**, dan **Bulanan** Anda."
            )
    else:
        t_cal  = profile["target_calories"]
        t_prot = profile["target_protein"]
        t_carb = profile["target_carbs"]
        t_fat  = profile["target_fat"]
        today  = datetime.date.today()

        # ── Period selector ───────────────────────────────────────────────────────
        period = st.radio(
            "Periode:", ["Harian 📅", "Mingguan 📆", "Bulanan 🗓️"],
            horizontal=True, key="period_selector", label_visibility="collapsed",
        )
        st.divider()

        # ═══════════════════════ HARIAN ══════════════════════════════════════
        if period == "Harian 📅":
            selected_date = st.date_input(
                "Tanggal:", today, label_visibility="collapsed"
            ).strftime("%Y-%m-%d")

            logs       = database.get_daily_logs(selected_date)
            total_cal  = sum(l["calories"] for l in logs)
            total_prot = sum(l["protein"]  for l in logs)
            total_carb = sum(l["carbs"]    for l in logs)
            total_fat  = sum(l["fat"]      for l in logs)
            remaining  = max(0.0, t_cal - total_cal)
            pct        = min(1.0, total_cal / t_cal) if t_cal > 0 else 0.0

            with st.container(border=True):
                st.markdown("### 📊 Ringkasan Progress Harian")
                col_t, col_e, col_r = st.columns(3)
                with col_t:
                    st.metric("🎯 Target", f"{t_cal:.0f} kkal")
                with col_e:
                    st.metric("🍕 Dikonsumsi", f"{total_cal:.0f} kkal")
                with col_r:
                    st.metric("🔥 Sisa", f"{remaining:.0f} kkal")
                
                st.progress(pct)
                delta_val = total_cal - t_cal
                st.caption(
                    f"**{pct*100:.1f}% tercapai** &nbsp;·&nbsp; "
                    f"Delta: {'%+.0f' % delta_val} kkal"
                )

            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                with st.container(border=True):
                    st.metric("🥩 Protein", f"{total_prot:.1f}g",
                              delta=f"{total_prot - t_prot:+.1f}g", delta_color="inverse")
            with mc2:
                with st.container(border=True):
                    st.metric("🍞 Karbo", f"{total_carb:.1f}g",
                              delta=f"{total_carb - t_carb:+.1f}g", delta_color="inverse")
            with mc3:
                with st.container(border=True):
                    st.metric("🥑 Lemak", f"{total_fat:.1f}g",
                              delta=f"{total_fat - t_fat:+.1f}g", delta_color="inverse")

            with st.expander("📊 Grafik Makro Harian"):
                _plot_macro_bar(
                    targets=[t_prot,     t_carb,     t_fat],
                    consumed=[total_prot, total_carb, total_fat],
                    labels=["Protein", "Karbo", "Lemak"],
                )

        # ═══════════════════════ MINGGUAN ════════════════════════════════════════
        elif period == "Mingguan 📆":
            dates = [
                (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(6, -1, -1)
            ]
            daily_data = []
            for d in dates:
                logs_d = database.get_daily_logs(d)
                daily_data.append({
                    "date":     d,
                    "label":    datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%a %d"),
                    "calories": sum(l["calories"] for l in logs_d),
                    "protein":  sum(l["protein"]  for l in logs_d),
                    "carbs":    sum(l["carbs"]    for l in logs_d),
                    "fat":      sum(l["fat"]       for l in logs_d),
                })
            df         = pd.DataFrame(daily_data)
            avg_cal    = df["calories"].mean()
            hari_aktif = int((df["calories"] > 0).sum())

            with st.container(border=True):
                st.markdown("### 📆 7 Hari Terakhir")
                wc1, wc2 = st.columns(2)
                wc1.metric("Rata-rata Kalori", f"{avg_cal:.0f} kkal",
                           delta=f"{avg_cal - t_cal:+.0f} vs target", delta_color="inverse")
                wc2.metric("Hari Aktif Log", f"{hari_aktif} / 7 hari")

            wa1, wa2 = st.columns(2)
            with wa1:
                with st.container(border=True):
                    st.metric("🥩 Avg Protein", f"{df['protein'].mean():.1f}g")
            with wa2:
                with st.container(border=True):
                    st.metric("🍞 Avg Karbo", f"{df['carbs'].mean():.1f}g")

            plt.style.use("seaborn-v0_8-whitegrid")
            fig, ax = plt.subplots(figsize=(5, 3))
            fig.patch.set_alpha(0)
            ax.set_facecolor("none")
            colors = ["#3B7DD8" if c > 0 else "#E2E8F0" for c in df["calories"]]
            ax.bar(df["label"], df["calories"], color=colors, alpha=0.9, width=0.6)
            ax.axhline(t_cal, color="#94A3B8", linestyle="--", linewidth=1.5,
                       label=f"Target {t_cal:.0f} kkal")
            ax.set_ylabel("Kalori (kkal)", fontsize=9)
            ax.tick_params(axis="x", labelsize=8, rotation=25)
            ax.tick_params(axis="y", labelsize=8)
            ax.legend(frameon=False, fontsize=8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            plt.tight_layout()
            st.pyplot(fig)

        # ═══════════════════════ BULANAN ═════════════════════════════════════════
        elif period == "Bulanan 🗓️":
            dates = [
                (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(29, -1, -1)
            ]
            daily_data = []
            for d in dates:
                logs_d = database.get_daily_logs(d)
                daily_data.append({"date": d, "calories": sum(l["calories"] for l in logs_d)})

            df          = pd.DataFrame(daily_data)
            df["date"]  = pd.to_datetime(df["date"])
            avg_cal     = df["calories"].mean()
            active_days = int((df["calories"] > 0).sum())

            with st.container(border=True):
                st.markdown("### 🗓️ 30 Hari Terakhir")
                mc1, mc2 = st.columns(2)
                mc1.metric("Rata-rata Kalori", f"{avg_cal:.0f} kkal",
                           delta=f"{avg_cal - t_cal:+.0f} vs target", delta_color="inverse")
                mc2.metric("Hari Aktif Log", f"{active_days} / 30 hari")

            plt.style.use("seaborn-v0_8-whitegrid")
            fig, ax = plt.subplots(figsize=(5, 3))
            fig.patch.set_alpha(0)
            ax.set_facecolor("none")
            ax.fill_between(df["date"], df["calories"], alpha=0.12, color="#3B7DD8")
            ax.plot(df["date"], df["calories"], color="#3B7DD8", linewidth=2)
            ax.axhline(t_cal, color="#94A3B8", linestyle="--", linewidth=1.5, label="Target")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
            ax.tick_params(axis="x", labelsize=8, rotation=30)
            ax.tick_params(axis="y", labelsize=8)
            ax.set_ylabel("Kalori (kkal)", fontsize=9)
            ax.legend(frameon=False, fontsize=8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            plt.tight_layout()
            st.pyplot(fig)

        # ── Weight trend — always visible at bottom of Insights ──────────────────
        st.divider()
        with st.expander("⚖️ Tren Berat Badan"):
            wlogs = database.get_weight_logs()
            if wlogs:
                df_w = pd.DataFrame(wlogs).set_index("date")
                st.line_chart(df_w["weight"])
            else:
                st.info("Belum ada data berat badan. Log berat dari tab **🍕 Quick Log**.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: QUICK LOG — Gemini-Only AI Food Entry
# ══════════════════════════════════════════════════════════════════════════════
with tab_quicklog:
    if not profile:
        # ── Welcome state: guide user to setup tab ───────────────────────────
        with st.container(border=True):
            st.markdown("### 🍕 Siap mencatat makanan?")
            st.write(
                "Profil Anda belum diisi. Buka tab **👤 Lifestyle Setup** terlebih "
                "dahulu agar kami bisa menghitung target kalori harianmu secara akurat."
            )
    else:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        logs      = database.get_daily_logs(today_str)
        total_cal = sum(l["calories"] for l in logs)
        t_cal     = profile["target_calories"]
        remaining = max(0.0, t_cal - total_cal)
        pct       = min(1.0, total_cal / t_cal) if t_cal > 0 else 0.0

        # Compact progress banner
        with st.container(border=True):
            st.caption(
                f"Hari ini: **{total_cal:.0f} / {t_cal:.0f} kkal** "
                f"&nbsp;·&nbsp; Sisa: **{remaining:.0f} kkal**"
            )
            st.progress(pct)

        # ── AI Food Entry ───────────────────────────────────────────────────
        st.subheader("🍕 Apa yang kamu makan?")

        if not status["configured"]:
            st.warning(
                "🔒 **Fitur AI terkunci.** Masukkan Gemini API key pribadi Anda "
                "di tab **👤 Lifestyle Setup** untuk mengaktifkan pelacakan makro dinamis."
            )
        else:
            food_input = st.text_input(
                "Deskripsikan makanan atau minuman:",
                placeholder="cth: semangkuk bakso sapi isi 10 biji + es teh manis",
                key="quicklog_input",
                label_visibility="collapsed",
            )

            if st.button("✨ Analisis & Estimasi via Gemini", type="primary", use_container_width=True):
                if not food_input.strip():
                    st.warning("Tulis dulu makanan atau minuman Anda di atas.")
                else:
                    with st.spinner("Gemini sedang menganalisis kandungan gizi makanan Anda..."):
                        result = ai_client.estimate_food_nutrition(food_input, api_key=_user_key)
                    if result:
                        st.session_state.ai_preview = result
                    else:
                        st.error(
                            "⚠️ Gagal mengestimasi. Coba deskripsikan lebih detail "
                            "atau periksa koneksi internet Anda."
                        )

            # ── AI Preview card ────────────────────────────────────────────────
            if st.session_state.ai_preview:
                r = st.session_state.ai_preview
                with st.container(border=True):
                    st.success(f"**{r['food_name']}**")
                    st.caption(f"_{r['serving_description']}_")
                    p1, p2 = st.columns(2)
                    p1.metric("🔥 Kalori",      f"{r['calories']:.0f} kkal")
                    p2.metric("🥩 Protein",     f"{r['protein_g']:.1f} g")
                    p3, p4 = st.columns(2)
                    p3.metric("🍞 Karbohidrat", f"{r['carbs_g']:.1f} g")
                    p4.metric("🥑 Lemak",        f"{r['fat_g']:.1f} g")

                    bc1, bc2 = st.columns(2)
                    if bc1.button("✅ Catat Sekarang", type="primary", use_container_width=True):
                        database.add_custom_food(
                            r["food_name"], r["calories"],
                            r["protein_g"], r["carbs_g"], r["fat_g"], "AI Entry"
                        )
                        conn   = database.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM foods WHERE name = ?", (r["food_name"],))
                        row    = cursor.fetchone()
                        conn.close()
                        if row:
                            database.log_food_consumption(today_str, row["id"], 1.0)
                            st.session_state.ai_preview = None
                            st.rerun()
                        else:
                            st.error("Gagal menyimpan ke database. Coba lagi.")

                    if bc2.button("✖ Batal", use_container_width=True):
                        st.session_state.ai_preview = None
                        st.rerun()

        st.divider()

        # ── Today's stacked log — one card per item, delete below each ────────
        st.subheader("📋 Log Hari Ini")
        if logs:
            for log in logs:
                with st.container(border=True):
                    st.markdown(f"**{log['food_name']}** &nbsp;×&nbsp; {log['quantity']:.1f}")
                    st.caption(
                        f"🔥 {log['calories']:.0f} kkal &nbsp;·&nbsp; "
                        f"🥩 {log['protein']:.1f}g &nbsp;·&nbsp; "
                        f"🍞 {log['carbs']:.1f}g &nbsp;·&nbsp; "
                        f"🥑 {log['fat']:.1f}g"
                    )
                    if st.button("🗑️ Hapus", key=f"del_{log['id']}", use_container_width=True):
                        database.delete_daily_log(log["id"])
                        st.rerun()
        else:
            st.info("Belum ada catatan hari ini. Gunakan input di atas untuk memulai.")

        st.divider()

        # ── AI Bulking Advisor ────────────────────────────────────────────────
        with st.expander("🤖 Saran Bulking dari Gemini"):
            if not status["configured"]:
                st.warning("🔒 Fitur ini membutuhkan API key. Buka tab **👤 Lifestyle Setup** untuk menambahkannya.")
            else:
                st.caption(f"Defisit hari ini: **{remaining:.0f} kkal**")
                if profile.get("likes_text"):
                    st.caption(
                        f"🟢 Preferensi Anda: "
                        f"_{profile['likes_text'][:70]}{'...' if len(profile.get('likes_text','')) > 70 else ''}_"
                    )
                if st.button("✨ Generate Saran Personal", type="primary",
                             use_container_width=True, key="advisor_btn"):
                    if remaining <= 50:
                        st.success("🎉 Target kalori hampir terpenuhi hari ini! Pertahankan.")
                    else:
                        with st.spinner("Gemini menyusun rekomendasi personal untuk Anda..."):
                            advice = ai_client.get_bulking_advice(
                                deficit_kcal=remaining,
                                target_kcal=t_cal,
                                likes_text=profile.get("likes_text", ""),
                                dislikes_text=profile.get("dislikes_text", ""),
                                api_key=_user_key,
                            )
                        if advice:
                            st.success(f"🎉 **{len(advice)} rekomendasi** dari Gemini:")
                            for i, item in enumerate(advice, 1):
                                with st.container(border=True):
                                    st.markdown(f"**{i}. {item['suggestion']}**")
                                    st.caption(item["reason"])
                                    st.metric("~Kalori", f"{item['estimated_calories']} kkal")
                        else:
                            st.error("⚠️ Gagal mendapat saran. Cek API Key atau koneksi internet.")

        # ── Weight log ────────────────────────────────────────────────────────
        with st.expander("⚖️ Log Berat Badan"):
            with st.container(border=True):
                bb_val = st.number_input(
                    "Berat hari ini (kg):", min_value=30.0, max_value=200.0,
                    value=float(profile["weight"]), step=0.1,
                )
                if st.button("💾 Simpan Berat", use_container_width=True, key="save_weight"):
                    database.log_weight(today_str, bb_val)
                    st.success("✅ Berat badan berhasil dicatat!")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: LIFESTYLE SETUP — AI Activity Profiling (no dropdown)
# ══════════════════════════════════════════════════════════════════════════════
with tab_setup:
    st.subheader("👤 Lifestyle Setup")
    st.caption(
        "Ceritakan gaya hidup Anda dalam bahasa bebas — "
        "AI akan menghitung kebutuhan kalori sejati Anda."
    )

    # ── Personal Gemini API Key ────────────────────────────────────────────────
    st.markdown("#### 🔑 Gemini API Key Pribadi")
    st.caption(
        "Key Anda hanya tersimpan di session browser ini dan tidak pernah dikirim "
        "ke server kami. Dapatkan key gratis di "
        "[aistudio.google.com](https://aistudio.google.com/app/apikey)."
    )
    with st.container(border=True):
        key_input = st.text_input(
            "Masukkan Gemini API Key Anda:",
            value=st.session_state.user_gemini_key,
            type="password",
            placeholder="AIzaSy...",
            key="gemini_key_input",
            label_visibility="collapsed",
        )
        if key_input != st.session_state.user_gemini_key:
            st.session_state.user_gemini_key = key_input
            st.rerun()
        if ai_client.is_key_valid(st.session_state.user_gemini_key):
            st.success("✅ API Key aktif — semua fitur AI diaktifkan.")
        else:
            st.warning("⚠️ Masukkan API key di atas untuk mengaktifkan fitur AI.")

    st.divider()

    # ── Physical data ─────────────────────────────────────────────────────
    st.markdown("#### 📐 Data Fisik")
    nama   = st.text_input("Nama Lengkap", value=profile["name"] if profile else "User")
    umur   = st.number_input("Umur (Tahun)", min_value=5, max_value=100,
                              value=profile["age"] if profile else 25)
    gender = st.radio(
        "Gender", ["Pria", "Wanita"], horizontal=True,
        index=0 if (not profile or profile["gender"] == "Pria") else 1,
    )
    col_a, col_b = st.columns(2)
    berat  = col_a.number_input("Berat (kg)", min_value=20.0, max_value=250.0,
                                 value=float(profile["weight"]) if profile else 65.0, step=0.1)
    tinggi = col_b.number_input("Tinggi (cm)", min_value=100.0, max_value=250.0,
                                 value=float(profile["height"]) if profile else 170.0, step=0.5)
    target_weight = st.number_input(
        "Target Berat (kg)", min_value=20.0, max_value=250.0,
        value=float(profile["target_weight"]) if profile else 72.0, step=0.1,
    )

    st.divider()

    # ── AI Activity Profiler — replaces rigid dropdown ────────────────────────
    st.markdown("#### 🏃 Gaya Hidup & Aktivitas Fisik")
    st.caption("Tulis dalam bahasa bebas. Gemini akan menentukan multiplier TDEE yang paling akurat.")

    activity_description = st.text_area(
        "Ceritakan aktivitas harian Anda:",
        value=profile.get("activity_description", "") if profile else "",
        placeholder=(
            "cth: Saya kerja kantoran dan duduk 8 jam sehari. "
            "Rutin jogging 30 menit 3 kali seminggu dan sesekali "
            "angkat beban ringan di gym Sabtu pagi..."
        ),
        height=120,
        label_visibility="collapsed",
    )

    # AI Analyze button — only shown if key valid and text is non-empty
    if status["configured"] and activity_description.strip():
        if st.button("🤖 Analisis Aktivitas via AI", use_container_width=True,
                     key="analyze_activity"):
            with st.spinner("Gemini sedang menganalisis pola aktivitas Anda..."):
                ai_act = ai_client.extract_activity_multiplier(
                    activity_description, api_key=_user_key
                )
            if ai_act:
                st.session_state.ai_activity_result = ai_act
                st.rerun()
            else:
                st.error("⚠️ Gagal menganalisis. Coba deskripsikan lebih spesifik.")
    elif not status["configured"]:
        st.info("💡 Masukkan API Key di atas untuk mengaktifkan AI activity analysis.")
    else:
        st.caption("_Tulis deskripsi aktivitas di atas lalu klik tombol Analisis._")

    # AI result card — preview TDEE before saving
    if st.session_state.ai_activity_result:
        res = st.session_state.ai_activity_result
        with st.container(border=True):
            st.success(
                f"**AI Hasil:** {res['activity_level']} "
                f"(multiplier: **{res['multiplier']:.3f}×**)"
            )
            st.caption(f"_{res['explanation']}_")
            # Live TDEE preview using current physical data inputs
            preview = engine.hitung_target_makro_dari_multiplier(
                berat, tinggi, umur, gender, res["multiplier"]
            )
            st.caption(
                f"📊 Preview: BMR **{preview['bmr']:.0f}** kkal "
                f"→ TDEE **{preview['tdee']:.0f}** kkal "
                f"→ Target (+400 surplus): **{preview['target_calories']:.0f}** kkal/hari"
            )

    st.divider()

    # ── Food preferences ──────────────────────────────────────────────────────
    st.markdown("#### 🍽️ Preferensi Makanan")
    st.caption("AI menggunakan ini untuk mempersonalisasi rekomendasi bulking Anda.")
    likes_text = st.text_area(
        "🟢 Makanan Favorit:",
        value=profile.get("likes_text", "") if profile else "",
        placeholder="cth: telur, tempe goreng, susu UHT, nasi padang, pisang, oat...",
        height=80,
    )
    dislikes_text = st.text_area(
        "🔴 Makanan yang Tidak Disukai:",
        value=profile.get("dislikes_text", "") if profile else "",
        placeholder="cth: bayam, sarden, jengkol...",
        height=80,
    )

    st.divider()

    # ── Save button ───────────────────────────────────────────────────────────
    if st.button("🔥 Simpan Profil", type="primary", use_container_width=True):
        ai_res = st.session_state.get("ai_activity_result")
        if ai_res and ai_res.get("multiplier"):
            multiplier = ai_res["multiplier"]
            act_level  = ai_res["activity_level"]
        elif profile and profile.get("activity_multiplier", 0) > 0:
            multiplier = float(profile["activity_multiplier"])
            act_level  = profile.get("activity_level", "Moderately Active")
        else:
            multiplier = 1.55  # safe default: Moderately Active
            act_level  = "Moderately Active"

        macros = engine.hitung_target_makro_dari_multiplier(
            berat, tinggi, umur, gender, multiplier
        )
        database.save_user_profile({
            "name":                 nama,
            "age":                  umur,
            "gender":               gender,
            "weight":               berat,
            "height":               tinggi,
            "activity_level":       act_level,
            "target_weight":        target_weight,
            "surplus_kcal":         400,
            "target_calories":      macros["target_calories"],
            "target_protein":       macros["target_protein"],
            "target_carbs":         macros["target_carbs"],
            "target_fat":           macros["target_fat"],
            "likes_text":           likes_text,
            "dislikes_text":        dislikes_text,
            "activity_description": activity_description,
            "activity_multiplier":  multiplier,
        })
        st.session_state.ai_activity_result = None
        st.success(
            f"🎉 Profil tersimpan! Target kalori: **{macros['target_calories']:.0f} kkal/hari** "
            f"(BMR {macros['bmr']:.0f} kkal × {multiplier:.3f}× + 400 surplus)"
        )
        st.rerun()

    # ── Current active targets summary ────────────────────────────────────────
    if profile:
        st.divider()
        st.subheader("🎯 Target Aktif")

        with st.container(border=True):
            st.metric("🔥 Target Kalori (surplus +400 kkal)",
                      f"{profile['target_calories']:,.0f} kkal")

        t1, t2 = st.columns(2)
        with t1:
            with st.container(border=True):
                st.metric("🥩 Protein", f"{profile['target_protein']:.0f} g")
        with t2:
            with st.container(border=True):
                st.metric("🍞 Karbo", f"{profile['target_carbs']:.0f} g")

        t3, t4 = st.columns(2)
        with t3:
            with st.container(border=True):
                st.metric("🥑 Lemak", f"{profile['target_fat']:.0f} g")
        with t4:
            with st.container(border=True):
                mult = profile.get("activity_multiplier", 0)
                st.metric("Multiplier AI", f"{mult:.3f}×" if mult else "Belum diset")

        if profile.get("activity_description"):
            with st.container(border=True):
                st.caption("🏃 **Deskripsi Aktivitas Tersimpan:**")
                st.write(profile["activity_description"])

        if profile.get("likes_text") or profile.get("dislikes_text"):
            with st.container(border=True):
                if profile.get("likes_text"):
                    st.markdown("**🟢 Favorit:** " + profile["likes_text"])
                if profile.get("dislikes_text"):
                    st.markdown("**🔴 Dihindari:** " + profile["dislikes_text"])
