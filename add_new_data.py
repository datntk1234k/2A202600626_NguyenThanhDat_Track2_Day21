import pandas as pd

df_train = pd.read_csv("data/train_phase1.csv")
df_new   = pd.read_csv("data/train_phase2.csv")

original_size = len(df_train)
df_updated = pd.concat([df_train, df_new], ignore_index=True)
df_updated.to_csv("data/train_phase1.csv", index=False)

print(f"Cap nhat du lieu: {original_size} -> {len(df_updated)} mau")
