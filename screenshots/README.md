# Screenshots cần nộp — NguyenThanhDat-2A202600626

Chụp các ảnh sau và lưu vào thư mục này (theo đúng tên gợi ý):

## Bước 1 — MLflow
- [ ] `01-mlflow-ui.png` — MLflow UI hiển thị **≥ 3 runs** với siêu tham số khác nhau
  (chạy `mlflow ui --backend-store-uri sqlite:///mlflow.db` → http://localhost:5000)
- [ ] `01-metrics.png` — một run cho thấy có cả `accuracy` và `f1_score`

## Bước 2 — CI/CD + Serving (model phase1 ~0.686, gate 0.70 sẽ CHẶN deploy)
- [ ] `02-eval-gate-block.png` — tab GitHub Actions cho thấy job **Eval chặn deploy** vì accuracy < 0.70
  (đây chính là bằng chứng eval-gate hoạt động — 4 điểm)
- [ ] `02-s3-data.png` — AWS S3 Console: bucket `mlops-day21-nguyenthanhdat-626` có dữ liệu dưới `dvc/`

## Bước 3 — Continuous training (sau `python add_new_data.py` → 5996 mẫu ~0.75)
- [ ] `03-actions-all-green.png` — tab Actions: **cả 4 job xanh** (Unit Test, Train, Eval, Deploy)
- [ ] `03-trigger-by-data.png` — run Actions có commit message là commit dữ liệu (chứng minh pipeline kích hoạt bởi data)
- [ ] `03-s3-model.png` — S3 Console: file model dưới `models/latest/model.pkl`
- [ ] `03-curl.png` — kết quả `curl http://VM_IP:8000/health` và `curl .../predict`

> Lưu ý: ảnh phải hiển thị repo/tài khoản/identity CỦA BẠN (NguyenThanhDat-2A202600626), không dùng ảnh của người khác.
