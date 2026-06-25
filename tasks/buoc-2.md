# Bước 2 - Pipeline CI/CD Tự Động (AWS)

Mục tiêu: Mỗi khi bạn push code hoặc thay đổi dữ liệu, GitHub Actions tự động huấn luyện mô hình, kiểm tra accuracy có đạt ngưỡng hay không, và triển khai lên EC2 nếu đạt yêu cầu.

Thời gian ước tính: 4-5 giờ

---

## Lựa Chọn Cloud Provider

Lab này được cấu hình sẵn cho **AWS**. Bảng ánh xạ khái niệm (nếu bạn muốn so sánh với các provider khác):

| Khái niệm | AWS (dùng trong lab) | GCP | Azure |
|---|---|---|---|
| Object Storage | Amazon S3 | Google Cloud Storage (GCS) | Azure Blob Storage |
| VM | EC2 | Compute Engine (GCE) | Azure Virtual Machine |
| CLI | `aws` | `gcloud` / `gsutil` | `az` |
| DVC storage extra | `dvc[s3]` | `dvc[gs]` | `dvc[azure]` |
| Cloud SDK Python | `boto3` | `google-cloud-storage` | `azure-storage-blob` |
| Credentials | IAM Access Key / IAM Role | Service Account JSON | Service Principal / Connection String |

Cài đặt AWS CLI (nếu chưa có) và đăng nhập:

```bash
aws --version          # kiem tra da cai chua
aws configure          # nhap Access Key, Secret Key, region, output format
```

---

## 2.1 Tạo S3 Bucket

Tên bucket phải là **duy nhất trên toàn bộ AWS** (toàn cầu). Thay `<BUCKET_NAME>` và `<YOUR_AWS_REGION>` bằng giá trị của bạn (ví dụ region `ap-southeast-1` cho Singapore hoặc `us-east-1`).

```bash
export BUCKET=<BUCKET_NAME>
export AWS_REGION=<YOUR_AWS_REGION>

# Tao bucket
aws s3 mb s3://$BUCKET --region $AWS_REGION
```

Lưu ý: lệnh `aws s3 mb ... --region` đã tự xử lý `LocationConstraint` cho các region khác `us-east-1`.

Xác nhận bucket đã tạo:

```bash
aws s3 ls | grep $BUCKET
```

---

## 2.2 Tạo AWS Credentials (IAM User + Access Key)

AWS xác thực qua **IAM Access Key** (cho máy cá nhân và GitHub Actions) hoặc **IAM Role** (gắn trực tiếp vào EC2). Nguyên tắc quyền tối thiểu: chỉ cấp quyền đọc/ghi đúng bucket cần thiết.

```bash
# 1. Tao IAM user rieng cho lab
aws iam create-user --user-name mlops-lab-user

# 2. Tao policy chi cho phep doc/ghi DUNG bucket cua ban (quyen toi thieu)
cat > mlops-s3-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::$BUCKET"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::$BUCKET/*"]
    }
  ]
}
EOF

aws iam put-user-policy \
  --user-name mlops-lab-user \
  --policy-name mlops-s3-access \
  --policy-document file://mlops-s3-policy.json

# 3. Xuat Access Key (luu lai AccessKeyId va SecretAccessKey - chi hien thi 1 lan)
aws iam create-access-key --user-name mlops-lab-user
```

Lưu ý: KHÔNG commit Access Key / Secret Key vào git. Cấu hình chúng cục bộ bằng `aws configure` (lưu vào `~/.aws/credentials`) và đặt vào GitHub Secrets ở mục 2.9.

| Quyền | Sử dụng | Lý do |
|---|---|---|
| GetObject / PutObject / DeleteObject trên `bucket/*` | Nên dùng | DVC và boto3 cần đọc/ghi/xóa object trong bucket. |
| `s3:*` hoặc AdministratorAccess | Không dùng | Quá rộng, vi phạm nguyên tắc quyền tối thiểu. |

---

## 2.3 Cài Đặt DVC Với S3 Remote

```bash
dvc init

# Tro DVC den S3 bucket
dvc remote add -d myremote s3://$BUCKET/dvc

# Dat region cho remote (khop voi region cua bucket)
dvc remote modify myremote region $AWS_REGION

# Credentials: DVC (qua boto3) tu dong doc tu ~/.aws/credentials
# (da cau hinh boi `aws configure`) hoac tu bien moi truong
# AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY. Khong can ghi key vao .dvc/config.

# Theo doi cac file du lieu bang DVC
dvc add data/train_phase1.csv
dvc add data/eval.csv
dvc add data/train_phase2.csv

# Commit cac file con tro DVC vao git (KHONG phai file CSV)
git add data/train_phase1.csv.dvc data/eval.csv.dvc data/train_phase2.csv.dvc \
        .gitignore .dvc/config
git commit -m "feat: track datasets with DVC"

# Day cac file CSV len S3
dvc push
```

Xác nhận trên AWS Console (S3) hoặc bằng CLI rằng dữ liệu đã xuất hiện dưới prefix `dvc/`:

```bash
aws s3 ls s3://$BUCKET/dvc/ --recursive
```

---

## 2.4 Tạo EC2 Instance

Bạn có thể tạo EC2 bằng AWS Console (dễ hơn cho người mới) hoặc bằng CLI. Dưới đây là cách CLI. Cần một **key pair** SSH và một **security group** mở cổng 22 (SSH) và 8000 (inference API).

```bash
# 1. Tao key pair de SSH vao EC2 (luu file .pem)
aws ec2 create-key-pair --key-name mlops-key \
  --query 'KeyMaterial' --output text > ~/.ssh/mlops-key.pem
chmod 400 ~/.ssh/mlops-key.pem

# 2. Tao security group
SG_ID=$(aws ec2 create-security-group \
  --group-name mlops-serve-sg \
  --description "MLOps serve SG" \
  --query 'GroupId' --output text)

# 3. Mo cong 22 (SSH) va 8000 (API). Goi y: gioi han SSH ve IP cua ban thay vi 0.0.0.0/0.
aws ec2 authorize-security-group-ingress --group-id $SG_ID \
  --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID \
  --protocol tcp --port 8000 --cidr 0.0.0.0/0

# 4. Tim AMI Ubuntu 22.04 moi nhat cho region cua ban
AMI_ID=$(aws ssm get-parameters \
  --names /aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id \
  --query 'Parameters[0].Value' --output text)

# 5. Tao instance (t3.micro thuoc free-tier o nhieu region)
aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.micro \
  --key-name mlops-key \
  --security-group-ids $SG_ID \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=mlops-serve}]'

# 6. Lay IP cong khai cua instance (luu lai, can cho GitHub Secrets)
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=mlops-serve" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text
```

(Khuyến nghị nâng cao: thay vì dùng Access Key trên EC2, hãy gắn một **IAM Role** có quyền đọc S3 vào instance — xem mục 2.7.)

---

## 2.5 Cấu Hình EC2 (Thực Hiện Một Lần, Thủ Công)

SSH vào EC2 (user mặc định của Ubuntu AMI là `ubuntu`):

```bash
VM_IP=<YOUR_VM_IP>
ssh -i ~/.ssh/mlops-key.pem ubuntu@$VM_IP
```

Bên trong EC2, cài đặt các thư viện cần thiết:

```bash
sudo apt update && sudo apt install -y python3-pip
pip3 install fastapi uvicorn scikit-learn joblib boto3

mkdir -p ~/models ~/src
```

Thoát khỏi EC2. Nếu bạn KHÔNG dùng IAM Role (mục 2.7), cấu hình credentials cho user trên EC2 bằng `aws configure` (hoặc đặt key qua biến môi trường trong systemd ở mục 2.7).

Copy file `serve.py` lên EC2 (sau khi đã viết xong ở mục 2.6):

```bash
scp -i ~/.ssh/mlops-key.pem src/serve.py ubuntu@$VM_IP:~/src/serve.py
```

---

## 2.6 Viết `src/serve.py`

File này chạy trên EC2 và cung cấp REST API để nhận yêu cầu suy luận.

Nhiệm vụ:
1. Khi khởi động, tải file `model.pkl` từ S3 về máy.
2. Cung cấp endpoint `GET /health` trả về trạng thái server.
3. Cung cấp endpoint `POST /predict` nhận 12 đặc trưng và trả về nhãn dự đoán.

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import boto3
import joblib
import os

app = FastAPI()

# Doc ten bucket tu bien moi truong (duoc dat trong systemd service)
S3_BUCKET = os.environ["S3_BUCKET"]
S3_MODEL_KEY = "models/latest/model.pkl"
MODEL_PATH = os.path.expanduser("~/models/model.pkl")


def download_model():
    """Tai file model.pkl tu S3 ve may khi server khoi dong."""
    # TODO 2.6.1: Tao S3 client bang boto3.client("s3")
    # TODO 2.6.2: Tai file ve bang s3.download_file(S3_BUCKET, S3_MODEL_KEY, MODEL_PATH)
    # TODO 2.6.3: In thong bao thanh cong
    pass  # xoa dong nay khi da viet xong


# Goi ham nay khi module duoc import (chay khi server khoi dong)
download_model()
model = joblib.load(MODEL_PATH)


class PredictRequest(BaseModel):
    features: list[float]


@app.get("/health")
def health():
    """Endpoint kiem tra suc khoe server. GitHub Actions dung endpoint nay de xac nhan deploy thanh cong."""
    # TODO 2.6.4: Tra ve dict {"status": "ok"}
    pass  # xoa dong nay khi da viet xong


@app.post("/predict")
def predict(req: PredictRequest):
    """
    Endpoint suy luan.

    Dau vao: JSON {"features": [f1, f2, ..., f12]}
    Dau ra:  JSON {"prediction": <0|1|2>, "label": <"thap"|"trung_binh"|"cao">}
    """
    # TODO 2.6.5: Kiem tra len(req.features) == 12.
    #   Neu khong, raise HTTPException(status_code=400, detail="Expected 12 features (wine quality)")

    # TODO 2.6.6: Goi model.predict([req.features]) de lay ket qua du doan.

    # TODO 2.6.7: Tra ve dict chua "prediction" (int) va "label" (string).
    #   Nhan: 0 -> "thap", 1 -> "trung_binh", 2 -> "cao"
    pass  # xoa dong nay khi da viet xong


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Upload file `serve.py` lên EC2:

```bash
scp -i ~/.ssh/mlops-key.pem src/serve.py ubuntu@$VM_IP:~/src/serve.py
```

---

## 2.7 Cấu Hình Systemd Service Trên EC2

SSH trở lại vào EC2:

```bash
ssh -i ~/.ssh/mlops-key.pem ubuntu@$VM_IP
```

Tạo file service để server tự động khởi động lại khi EC2 reboot.

**Cách A (khuyến nghị) — dùng IAM Role:** Gắn một IAM Role có quyền đọc S3 (`s3:GetObject` trên `bucket/*`) vào instance qua AWS Console (Actions > Security > Modify IAM role). Khi đó boto3 trên EC2 tự lấy credentials, KHÔNG cần đặt Access Key:

```bash
sudo tee /etc/systemd/system/mlops-serve.service > /dev/null <<EOF
[Unit]
Description=MLOps Model Inference Server
After=network.target

[Service]
User=$USER
WorkingDirectory=/home/$USER
Environment="S3_BUCKET=<YOUR_BUCKET_NAME>"
Environment="AWS_DEFAULT_REGION=<YOUR_AWS_REGION>"
ExecStart=/usr/bin/python3 /home/$USER/src/serve.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

**Cách B — dùng Access Key:** Nếu không dùng IAM Role, thêm hai dòng credentials vào phần `[Service]`:

```ini
Environment="AWS_ACCESS_KEY_ID=<YOUR_ACCESS_KEY_ID>"
Environment="AWS_SECRET_ACCESS_KEY=<YOUR_SECRET_ACCESS_KEY>"
```

Kích hoạt service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mlops-serve
```

Thay `<YOUR_BUCKET_NAME>` và `<YOUR_AWS_REGION>` bằng giá trị thực của bạn.

Chưa cần khởi động service lúc này. Model chưa có trên S3 cho đến khi pipeline CI/CD chạy lần đầu tiên.

---

## 2.8 SSH Key Để GitHub Actions Deploy

Job Deploy SSH vào EC2 để restart service. Có hai lựa chọn:

- **Dùng lại key pair `mlops-key.pem`** đã tạo ở mục 2.4 (đơn giản nhất): dán nội dung file `~/.ssh/mlops-key.pem` vào secret `VM_SSH_KEY`.
- **Tạo key riêng cho deploy** (tách biệt hơn):

```bash
ssh-keygen -t ed25519 -f ~/.ssh/mlops_deploy -N "" -C "github-actions-deploy"

# Them public key vao EC2
ssh -i ~/.ssh/mlops-key.pem ubuntu@$VM_IP \
  "echo '$(cat ~/.ssh/mlops_deploy.pub)' >> ~/.ssh/authorized_keys"
```

Khi đó dùng nội dung `~/.ssh/mlops_deploy` (private key) cho secret `VM_SSH_KEY`.

---

## 2.9 Thêm GitHub Secrets

Vào repo GitHub: Settings > Secrets and variables > Actions > New repository secret.

Thêm chính xác các secrets sau:

| Tên secret | Cách lấy giá trị |
|---|---|
| AWS_ACCESS_KEY_ID | Access Key ID của IAM user (mục 2.2) |
| AWS_SECRET_ACCESS_KEY | Secret Access Key của IAM user (mục 2.2) |
| AWS_REGION | Region của bucket/EC2 (ví dụ: `ap-southeast-1`) |
| CLOUD_BUCKET | Tên S3 bucket (ví dụ: `my-mlops-bucket`) |
| VM_HOST | IP công khai của EC2 (mục 2.4) |
| VM_USER | User SSH trên EC2 (Ubuntu AMI là `ubuntu`) |
| VM_SSH_KEY | Toàn bộ nội dung private key (`.pem` hoặc `mlops_deploy`), gồm cả dòng `-----BEGIN ... PRIVATE KEY-----` |

Kiểm tra: Mỗi secret khi dán vào phải không có khoảng trắng thừa ở đầu hoặc cuối.

---

## 2.10 Viết `tests/test_train.py`

Các test này chạy trên dữ liệu nhỏ tạo trong bộ nhớ (không cần pull DVC), đảm bảo chạy được trong GitHub Actions mà không cần xác thực S3.

Tạo file `tests/test_train.py` theo khung dưới đây:

```python
import os
import json
import numpy as np
import pandas as pd
from src.train import train


FEATURE_NAMES = [
    "fixed_acidity", "volatile_acidity", "citric_acid", "residual_sugar",
    "chlorides", "free_sulfur_dioxide", "total_sulfur_dioxide", "density",
    "pH", "sulphates", "alcohol", "wine_type",
]


def _make_temp_data(tmp_path):
    """Tao dataset nho voi cung schema Wine Quality de su dung trong test."""
    rng = np.random.default_rng(0)
    n = 200
    # TODO 2.10.1: Tao mang X co kich thuoc (n, len(FEATURE_NAMES)) voi gia tri ngau nhien [0, 1)
    # TODO 2.10.2: Tao mang y co n phan tu, moi phan tu la so nguyen ngau nhien trong [0, 3)
    # TODO 2.10.3: Tao DataFrame tu X voi cac cot la FEATURE_NAMES, them cot "target" = y
    # TODO 2.10.4: Luu 160 dong dau vao file train.csv va 40 dong cuoi vao file eval.csv tai tmp_path
    # TODO 2.10.5: Tra ve (train_path, eval_path)
    pass  # xoa dong nay khi da viet xong


def test_train_returns_float(tmp_path):
    """Kiem tra ham train() tra ve mot so thuc trong khoang [0, 1]."""
    train_path, eval_path = _make_temp_data(tmp_path)
    # TODO 2.10.6: Goi ham train() voi sieu tham so nho (n_estimators=10, max_depth=3)
    # TODO 2.10.7: assert ket qua tra ve la float va nam trong [0.0, 1.0]
    pass  # xoa dong nay khi da viet xong


def test_metrics_file_created(tmp_path):
    """Kiem tra file outputs/metrics.json duoc tao sau khi huan luyen."""
    train_path, eval_path = _make_temp_data(tmp_path)
    train(
        {"n_estimators": 10, "max_depth": 3},
        data_path=train_path,
        eval_path=eval_path,
    )
    # TODO 2.10.8: assert file "outputs/metrics.json" ton tai
    # TODO 2.10.9: Doc file metrics.json va assert no chua ca "accuracy" va "f1_score"
    pass  # xoa dong nay khi da viet xong


def test_model_file_created(tmp_path):
    """Kiem tra file models/model.pkl duoc tao sau khi huan luyen."""
    train_path, eval_path = _make_temp_data(tmp_path)
    train(
        {"n_estimators": 10, "max_depth": 3},
        data_path=train_path,
        eval_path=eval_path,
    )
    # TODO 2.10.10: assert file "models/model.pkl" ton tai
    pass  # xoa dong nay khi da viet xong
```

Chạy thử test cục bộ trước khi commit:

```bash
pytest tests/ -v
```

Ba test đều phải qua trước khi tiếp tục.

---

## 2.11 Viết `.github/workflows/mlops.yml`

Pipeline gồm bốn jobs chạy theo thứ tự: Unit Test -> Train -> Eval -> Deploy.

Tạo file `.github/workflows/mlops.yml` theo khung dưới đây:

```yaml
name: MLOps Pipeline

on:
  push:
    branches: [main, master]
    paths:
      - 'data/**.dvc'
      - 'src/**.py'
      - 'params.yaml'
  workflow_dispatch:

jobs:

  # JOB 1: Chay unit tests tren du lieu ao (khong can S3)
  test:
    name: Unit Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        # TODO 2.11.1: Chay pytest tren thu muc tests/ voi co -v
        run: # <dien lenh o day>

  # JOB 2: Huan luyen mo hinh tren du lieu thuc, upload artifact len S3
  train:
    name: Train
    needs: test
    runs-on: ubuntu-latest
    outputs:
      accuracy: ${{ steps.read_metrics.outputs.accuracy }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Authenticate to AWS
        # TODO 2.11.2: Dung action aws-actions/configure-aws-credentials@v4
        #   voi 3 secret: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION.
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Pull data with DVC
        # TODO 2.11.3: Dung dvc pull de tai train_phase1.csv va eval.csv tu S3
        run: # <dien lenh o day>

      - name: Train model
        run: python src/train.py

      - name: Read metrics
        id: read_metrics
        # TODO 2.11.4: Doc "accuracy" tu outputs/metrics.json va set thanh output.
        run: |
          # <dien code o day>

      - name: Upload model to S3
        # TODO 2.11.5: Dung boto3 de upload models/model.pkl len
        #   s3://<bucket>/models/latest/model.pkl  (bucket lay tu secret CLOUD_BUCKET)
        env:
          CLOUD_BUCKET: ${{ secrets.CLOUD_BUCKET }}
        run: |
          python - <<'EOF'
          # <dien code Python o day>
          EOF

  # JOB 3: Kiem tra chat luong - chi cho phep deploy khi accuracy dat nguong
  eval:
    name: Eval
    needs: train
    runs-on: ubuntu-latest
    steps:
      - name: Check eval gate
        # TODO 2.11.6: Doc accuracy tu output cua job train, float() roi so sanh nguong.
        run: |
          python - <<'EOF'
          # <dien code Python o day>
          EOF

  # JOB 4: Trien khai sau khi eval gate qua
  deploy:
    name: Deploy
    needs: eval
    runs-on: ubuntu-latest
    steps:
      - name: SSH deploy to EC2
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.VM_HOST }}
          username: ${{ secrets.VM_USER }}
          key: ${{ secrets.VM_SSH_KEY }}
          script: |
            # TODO 2.11.7: Restart service mlops-serve tren EC2.
            # TODO 2.11.8: Cho server san sang (sleep 5) roi curl /health de xac nhan.
            # <dien lenh bash o day>
```

(File `mlops.yml` trong repo này đã được điền sẵn đầy đủ cho AWS — bạn có thể dùng làm tham chiếu.)

---

## 2.12 Lần Chạy Pipeline Đầu Tiên

Tạo hai file `__init__.py` trong `src/` và `tests/` để Python có thể import module:

```bash
touch src/__init__.py tests/__init__.py
```

Push tất cả lên GitHub:

```bash
git add .
git commit -m "feat: add CI/CD pipeline, tests, and serving API"
git push origin main
```

Theo dõi pipeline trong tab **Actions** trên repo GitHub.

Sau khi pipeline chạy thành công và model đã được upload lên S3, khởi động service trên EC2:

```bash
ssh -i ~/.ssh/mlops-key.pem ubuntu@$VM_IP "sudo systemctl start mlops-serve"
```

Thử nghiệm endpoint:

```bash
VM_IP=<YOUR_VM_IP>

# Kiem tra suc khoe
curl http://$VM_IP:8000/health

# Du doan (12 dac trung theo thu tu trong FEATURE_NAMES)
curl -X POST http://$VM_IP:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [7.4, 0.70, 0.00, 1.9, 0.076, 11.0, 34.0, 0.9978, 3.51, 0.56, 9.4, 0]}'
```

Kết quả mong đợi:

```json
{"prediction": 0, "label": "thap"}
```

---

## Xử Lý Sự Cố

**`dvc push` thất bại với lỗi xác thực**

Xác nhận `aws configure` đã chạy và credentials hợp lệ:

```bash
aws sts get-caller-identity
cat .dvc/config
```

Đảm bảo region trong `.dvc/config` khớp với region của bucket. Nếu cần set lại:

```bash
dvc remote modify myremote region <YOUR_AWS_REGION>
```

**GitHub Actions `dvc pull` thất bại**

Kiểm tra 3 secret `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` đã đúng và IAM user có quyền đọc bucket (mục 2.2).

**Job Deploy thất bại dù accuracy có vẻ đủ cao**

GitHub Actions outputs là kiểu chuỗi. Đảm bảo code Python trong eval gate thực hiện `float()` trước khi so sánh.

**Service trên EC2 không khởi động được**

Xem log của service:

```bash
sudo journalctl -u mlops-serve -n 50
```

Nguyên nhân phổ biến:
- Biến môi trường `S3_BUCKET` sai trong file service.
- EC2 không có quyền đọc S3 (chưa gắn IAM Role hoặc Access Key sai trong systemd).
- File model chưa tồn tại trên S3 (service chỉ khởi động được sau khi pipeline lần đầu chạy thành công).

**Không SSH được vào EC2**

- Kiểm tra security group đã mở cổng 22.
- Đúng user (`ubuntu` cho Ubuntu AMI) và đúng file `.pem` (`chmod 400`).

---

## Kết Quả Cần Đạt - Bước 2

- Cả bốn GitHub Actions jobs (Unit Test, Train, Eval, Deploy) đều hoàn thành thành công (màu xanh).
- `curl http://VM_IP:8000/health` trả về `{"status": "ok"}`.
- `curl http://VM_IP:8000/predict` trả về kết quả dự đoán hợp lệ.
- S3 Console hiển thị file dữ liệu dưới `dvc/` và file model dưới `models/latest/model.pkl`.

Chụp màn hình tab Actions hiển thị cả bốn jobs màu xanh (cần nộp bài).

---

Tiếp theo: [Bước 3 - Huấn luyện liên tục](buoc-3.md)
</content>
