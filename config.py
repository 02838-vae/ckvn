# config.py
# Cấu hình xác thực và phiên làm việc

# --- USERS ---
# Mật khẩu được mã hóa bằng bcrypt (không lưu plaintext)
# Để thêm user mới, chạy lệnh sau và copy hash vào đây:
#   python -c "import bcrypt; print(bcrypt.hashpw(b'mat_khau_moi', bcrypt.gensalt()).decode())"

USERS = {
    "vae02838": "$2b$12$rSC/E/XElbru9GLalOfXkeNW.l8gdCRBw.vM2.h2rrAthHypN2NaG"
}

# --- PHIÊN LÀM VIỆC ---
# Tự động logout sau 1 giờ (3600 giây) không có thao tác
SESSION_TIMEOUT_SECONDS = 3600
