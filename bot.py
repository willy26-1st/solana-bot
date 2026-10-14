import requests
import time

# ==========================================
# KONFIGURASI BOT TELEGRAM & FILTER
# ==========================================
TELEGRAM_BOT_TOKEN = "8940610675:AAFDui2jclWI25hf4SWdh0g36tl2mZPAudo"
TELEGRAM_CHAT_ID = "6175028962u"

# Kriteria Filter Micro-Cap (Bebas Wash Trading)
MIN_LIQUIDITY = 10000        # Minimal Liquidity $10k
MIN_MARKET_CAP = 50000       # Minimal MCap $50k
MAX_MARKET_CAP = 1500000     # Maksimal MCap $1.5M
MIN_VOLUME = 50000           # Minimal Volume 24j $50k
MAX_VOL_LIQ_RATIO = 8.0      # Maksimal Rasio Volume/Liquidity (Diatas ini = Wash Trading)
MAX_TXNS_PER_SEC = 2.5       # Maksimal Transaksi/Detik (Diatas ini = Bot Wash Trading)

# Penyimpanan token yang sudah dikirim agar tidak terjadi spam notifikasi
notified_tokens = set()

def send_telegram_message(message):
    """Fungsi untuk mengirim pesan ke Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Gagal mengirim pesan Telegram: {e}")

def check_solana_pairs():
    """Fungsi utama memindai DEXScreener API"""
    print("🔎 Sedang memindai token terbaru di Solana...")

    # Endpoint DEXScreener untuk token/pair terbaru
    url = "https://api.dexscreener.com/token-profiles/latest/v1"

    try:
        response = requests.get("https://api.dexscreener.com/latest/dex/search?q=solana")
        if response.status_code != 200:
            print("Gagal mengambil data dari DEXScreener API")
            return

        data = response.json()
        pairs = data.get("pairs", [])

        for pair in pairs:
            # Pastikan hanya jaringan Solana
            if pair.get("chainId") != "solana":
                continue

            pair_address = pair.get("pairAddress")
            base_token = pair.get("baseToken", {})
            token_symbol = base_token.get("symbol", "UNKNOWN")
            token_address = base_token.get("address", "")

            # Lewati jika token sudah pernah dinotifikasikan
            if pair_address in notified_tokens:
                continue

            # Ambil data statistik
            liquidity = pair.get("liquidity", {}).get("usd", 0)
            mcap = pair.get("marketCap", 0) or pair.get("fdv", 0)
            volume_24h = pair.get("volume", {}).get("h24", 0)
            txns_24h = pair.get("txns", {}).get("h24", {})
            buys_24h = txns_24h.get("buys", 0)
            sells_24h = txns_24h.get("sells", 0)
            total_txns = buys_24h + sells_24h

            # Hitung indikator Wash Trading
            vol_liq_ratio = volume_24h / liquidity if liquidity > 0 else 999
            # Estimasi transaksi per detik dalam kurun 24 jam (86400 detik)
            txns_per_sec = total_txns / 86400

            # --------------------------------------------------
            # PENYARINGAN (FILTERING LOGIC)
            # --------------------------------------------------
            if liquidity < MIN_LIQUIDITY:
                continue
            if not (MIN_MARKET_CAP <= mcap <= MAX_MARKET_CAP):
                continue
            if volume_24h < MIN_VOLUME:
                continue

            # ELIMINASI WASH TRADING
            if vol_liq_ratio > MAX_VOL_LIQ_RATIO:
                # Rasio terlalu tinggi = indikasi perputaran volume palsu
                continue
            if txns_per_sec > MAX_TXNS_PER_SEC:
                # Frekuensi transaksi terlalu ekstrem = bot wash trading
                continue
            if buys_24h == 0 or sells_24h == 0:
                # Transaksi sepihak
                continue

            # --------------------------------------------------
            # HASIL LOLOS FILTER & KIRIM NOTIFIKASI
            # --------------------------------------------------
            notified_tokens.add(pair_address)

            message = (
                f"🚨 <b>POTENTIAL ORGANIC TOKEN DETECTED!</b> 🚨\n\n"
                f"🪙 <b>Token:</b> ${token_symbol}\n"
                f"📍 <b>CA:</b> <code>{token_address}</code>\n\n"
                f"📊 <b>Market Cap:</b> ${mcap:,.0f}\n"
                f"💧 <b>Liquidity:</b> ${liquidity:,.0f}\n"
                f"📈 <b>24h Vol:</b> ${volume_24h:,.0f}\n"
                f"⚖️ <b>Vol/Liq Ratio:</b> {vol_liq_ratio:.2f}x (Organik)\n"
                f"🔄 <b>Buys:</b> {buys_24h:,} | <b>Sells:</b> {sells_24h:,}\n\n"
                f"🔗 <b>Quick Links:</b>\n"
                f"• <a href='{pair.get('url')}'>Chart DEXScreener</a>\n"
                f"• <a href='https://rugcheck.xyz/tokens/{token_address}'>RugCheck Security</a>\n"
            )

            send_telegram_message(message)
            print(f"✅ Notifikasi terkirim untuk ${token_symbol}")

    except Exception as e:
        print(f"Error saat memproses data: {e}")

# Run Loop (Menjalankan bot setiap 60 detik)
if __name__ == "__main__":
    print("🚀 Bot Notifikasi Micro-Cap Berjalan...")
    while True:
        check_solana_pairs()
        time.sleep(60)
