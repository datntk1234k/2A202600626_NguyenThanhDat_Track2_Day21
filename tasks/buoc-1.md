# Bước 1 - Thực Nghiệm Cục Bộ và Theo Dõi Thí Nghiệm

Mục tiêu: Chạy ít nhất 3 thí nghiệm huấn luyện với các siêu tham số khác nhau. So sánh kết quả trong MLflow UI. Xác định bộ siêu tham số tốt nhất để sử dụng ở Bước 2.

Thời gian ước tính: 2-3 giờ

---

## 1.1 Tải Dữ Liệu

Chạy script đã được cung cấp sẵn (không cần sửa):

```bash
python generate_data.py
```

Kết quả mong đợi:

```
train_phase1.csv : 2998 mẫu
eval.csv         :  500 mẫu
train_phase2.csv : 2998 mẫu
```

Xác nhận các file đã được tạo:

```bash
ls data/
```

---

## 1.2 Cài Đặt Thư Viện

```bash
pip install -r requirements.txt
```

---

## 1.3 Cấu Hình MLflow

MLflow sử dụng SQLite làm backend lưu trữ cục bộ. Thêm hai biến môi trường sau vào shell hoặc file `.env`:

```bash
export MLFLOW_TRACKING_URI=sqlite:///mlflow.db
export MLFLOW_ARTIFACT_ROOT=./mlartifacts
```

Không cần khởi động server riêng. MLflow sẽ ghi dữ liệu thí nghiệm vào file cục bộ `mlflow.db`.

---

## 1.4 Viết `params.yaml`

Tạo file `params.yaml` ở thư mục gốc của project. File này chứa các siêu tham số cho mô hình RandomForest. Bạn sẽ thay đổi các giá trị này giữa các lần chạy để so sánh hiệu quả.

```yaml
n_estimators: 100
max_depth: 5
min_samples_split: 2
```

Giải thích từng tham số:

| Tham số | Ý nghĩa | Gợi ý giá trị thử nghiệm |
|---|---|---|
| n_estimators | Số lượng cây quyết định trong rừng | 50, 100, 200 |
| max_depth | Độ sâu tối đa của mỗi cây | 3, 5, 10, None |
| min_samples_split | Số mẫu tối thiểu để phân chia một nút | 2, 5, 10 |

---

## 1.5 Viết `src/train.py`

Tạo file `src/train.py` theo khung dưới đây. Các vị trí có nhãn `# TODO` là phần bạn cần viết code.

Nhiệm vụ của script này:
1. Đọc dữ liệu huấn luyện (`train_phase1.csv`) và dữ liệu đánh giá (`eval.csv`).
2. Huấn luyện mô hình `RandomForestClassifier` với các siêu tham số từ `params.yaml`.
3. Ghi kết quả (`accuracy`, `f1_score`) vào MLflow.
4. Lưu file `outputs/metrics.json` để CI/CD đọc ở Bước 2.
5. Lưu file `models/model.pkl` để triển khai ở Bước 2.

```python
import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
import json
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

EVAL_THRESHOLD = 0.70


def train(
    params: dict,
    data_path: str = "data/train_phase1.csv",
    eval_path: str = "data/eval.csv",
) -> float:
    """
    Huấn luyện mô hình và ghi nhận kết quả vào MLflow.

    Tham số:
        params: dict chứa các siêu tham số cho RandomForestClassifier
        data_path: đường dẫn đến file dữ liệu huấn luyện
        eval_path: đường dẫn đến file dữ liệu đánh giá

    Trả về:
        accuracy (float): độ chính xác trên tập đánh giá
    """

    # TODO 1.5.1: Đọc dữ liệu huấn luyện từ data_path vào DataFrame df_train
    #   và dữ liệu đánh giá từ eval_path vào DataFrame df_eval.
    # Gợi ý: sử dụng pd.read_csv(...)

    # TODO 1.5.2: Tách đặc trưng và nhãn.
    #   X_train, y_train từ df_train (bỏ cột "target")
    #   X_eval, y_eval từ df_eval (bỏ cột "target")

    # TODO 1.5.3: Bắt đầu một MLflow run bằng `with mlflow.start_run():`
    #   Bên trong block này, thực hiện các bước sau:

    #   TODO 1.5.4: Ghi nhận các siêu tham số vào MLflow.
    #   Gợi ý: mlflow.log_params(params)

    #   TODO 1.5.5: Khởi tạo và huấn luyện mô hình RandomForestClassifier.
    #   Gợi ý: model = RandomForestClassifier(**params, random_state=42)
    #          model.fit(X_train, y_train)

    #   TODO 1.5.6: Tính accuracy và f1_score trên tập đánh giá.
    #   Gợi ý: preds = model.predict(X_eval)
    #          acc = accuracy_score(y_eval, preds)
    #          f1  = f1_score(y_eval, preds, average="weighted")

    #   TODO 1.5.7: Ghi nhận các chỉ số vào MLflow.
    #   Gợi ý: mlflow.log_metric("accuracy", acc)
    #          mlflow.log_metric("f1_score", f1)

    #   TODO 1.5.8: Log mô hình vào MLflow artifact.
    #   Gợi ý: mlflow.sklearn.log_model(model, "model")

    #   TODO 1.5.9: In kết quả ra màn hình.
    #   Gợi ý: print(f"Accuracy: {acc:.4f} | F1: {f1:.4f}")

    #   TODO 1.5.10: Lưu metrics ra file outputs/metrics.json.
    #   File này sẽ được đọc bởi GitHub Actions ở Bước 2.
    #   Gợi ý:
    #       os.makedirs("outputs", exist_ok=True)
    #       with open("outputs/metrics.json", "w") as f:
    #           json.dump({"accuracy": acc, "f1_score": f1}, f)

    #   TODO 1.5.11: Lưu mô hình ra file models/model.pkl.
    #   File này sẽ được upload lên GCS ở Bước 2.
    #   Gợi ý:
    #       os.makedirs("models", exist_ok=True)
    #       joblib.dump(model, "models/model.pkl")

    # TODO 1.5.12: Trả về acc để các hàm gọi train() có thể đọc kết quả.
    pass  # xóa dòng này khi bạn đã viết xong


if __name__ == "__main__":
    # Đọc siêu tham số từ params.yaml và gọi hàm train()
    with open("params.yaml") as f:
        params = yaml.safe_load(f)
    train(params)
```

---

## 1.6 Chạy Ít Nhất 3 Thí Nghiệm

Chỉnh sửa `params.yaml` giữa mỗi lần chạy để thay đổi siêu tham số. Ví dụ:

```bash
# Lần 1: giá trị mặc định
python src/train.py

# Chỉnh sửa params.yaml -> n_estimators: 50, max_depth: 3
python src/train.py

# Chỉnh sửa params.yaml -> n_estimators: 200, max_depth: 10, min_samples_split: 5
python src/train.py
```

Gợi ý: Chạy thêm 1-2 lần nữa với các giá trị khác để có nhiều dữ liệu so sánh hơn.

---

## 1.7 Phân Tích Kết Quả Trên MLflow UI

Khởi động MLflow UI:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db
```

Truy cập http://localhost:5000. Bạn sẽ thấy tất cả các lần chạy được liệt kê.

Trong giao diện MLflow UI, hãy:

1. Sắp xếp các lần chạy theo `accuracy` (giảm dần) để tìm lần chạy tốt nhất.
2. Chọn nhiều lần chạy và nhấn "Compare" để xem biểu đồ so sánh.
3. Ghi nhận bộ siêu tham số của lần chạy có accuracy cao nhất.

Đặt bộ siêu tham số tốt nhất vào `params.yaml` trước khi chuyển sang Bước 2.

---

## Kết Quả Cần Đạt - Bước 1

Trước khi chuyển sang Bước 2, kiểm tra các điểm sau:

- `src/train.py` chạy thành công không có lỗi.
- File `outputs/metrics.json` tồn tại và chứa cả `accuracy` và `f1_score`.
- File `models/model.pkl` tồn tại.
- MLflow UI hiển thị ít nhất 3 lần chạy với các siêu tham số khác nhau.
- `params.yaml` đã được cập nhật với bộ siêu tham số tốt nhất.

Chụp màn hình MLflow UI (cần nộp bài).

---

Tiếp theo: [Bước 2 - Pipeline CI/CD tự động](buoc-2.md)
