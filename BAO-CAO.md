# Báo Cáo Lab Day 21 — MLOps CI/CD trên AWS

- **Họ tên / Mã số:** Nguyễn Thanh Đạt — 2A202600626
- **Repo:** https://github.com/datntk1234k/2A202600626_NguyenThanhDat_Track2_Day21
- **Cloud:** AWS (S3 `mlops-day21-nguyenthanhdat-626` — ap-southeast-1, EC2 t3.micro)

## 1. Bộ siêu tham số đã chọn và lý do

Đã chạy 4 thí nghiệm trên MLflow (tập `train_phase1.csv`, 2998 mẫu):

| Run | n_estimators | max_depth | min_samples_split | Accuracy |
|---|---|---|---|---|
| 1 | 100 | 5 | 2 | 0.5640 |
| 2 | 200 | 10 | 5 | 0.6420 |
| 3 | 180 | 20 | 2 | 0.6860 |
| **4 (chọn)** | **300** | **None** | **2** | **0.6860** |

**Lý do chọn run 4** (`n_estimators=300, max_depth=None`): cho accuracy cao nhất và ổn định nhất. `max_depth` lớn (không giới hạn) giúp cây học được các quan hệ phi tuyến trong dữ liệu hóa học của rượu vang; tăng `n_estimators` lên 300 giúp giảm phương sai của rừng. Khi áp dụng lên tập dữ liệu đầy đủ (5996 mẫu sau Bước 3), bộ tham số này đạt **accuracy 0.7540**, vượt ngưỡng 0.70.

## 2. Kết quả pipeline

| Giai đoạn | Dữ liệu | Accuracy | Eval gate (0.70) | Deploy |
|---|---|---|---|---|
| Bước 2 | phase1 (2998) | 0.686 | ❌ chặn | bị hủy (đúng thiết kế) |
| Bước 3 | phase1+phase2 (5996) | 0.754 | ✅ qua | triển khai thành công |

Thêm dữ liệu mới làm accuracy tăng từ 0.686 → 0.754, chứng minh giá trị của continuous training.

## 3. Khó khăn gặp phải và cách giải quyết

1. **Bài gốc cấu hình cho GCP** — đã chuyển toàn bộ sang AWS: `dvc[s3]`, `boto3`, `aws-actions/configure-aws-credentials`, S3 thay GCS, EC2 thay GCE.
2. **Python cục bộ (Homebrew 3.13) bị hỏng `pyexpat`** — không tạo được venv. Khắc phục bằng cách dùng Python hệ thống của Apple (`/usr/bin/python3`) để tạo venv.
3. **Xung đột `boto3`/`botocore` với `aiobotocore` (dvc[s3])** khiến pip backtrack rất lâu — ghim `boto3==1.41.4`, `botocore==1.41.5`.
4. **MLflow 3.x cấm file store mặc định `./mlruns`** làm unit test fail trên CI — đặt `MLFLOW_TRACKING_URI=sqlite:///mlflow.db` mặc định trong `train.py`.
5. **IAM user của lab không có quyền S3** — tự cấp inline policy S3 (giới hạn ở bucket `mlops-day21-*`) nhờ quyền IAMFullAccess.
6. **EC2 không cần lưu secret** — dùng IAM Role gắn trực tiếp vào instance để boto3 đọc model từ S3.
7. **Deploy SSH fail (`no key found`)** — secret `VM_SSH_KEY` ban đầu paste sai; set lại bằng nội dung đầy đủ của file `.pem`.
</content>
