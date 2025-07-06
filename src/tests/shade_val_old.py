import rasterio
import numpy as np
from sklearn.metrics import confusion_matrix, cohen_kappa_score
import pandas as pd
from pathlib import Path

"""
1) load the checked rasters - using DSM (bldg height)
2) error, r-squred, sd
"""

global_path = "/Users/hyejijoh/Documents/wri_proj/Amsterdam/data/ctcm/global/output/global_shadow_2023_189_1200D.tif"
local_path = "/Users/hyejijoh/Documents/wri_proj/Amsterdam/data/ctcm/local/output/all_local_manual_shadow_2023_189_1200D.tif"
time = "1200"
output_dir = Path("results/shade")
output_dir.mkdir(parents=True, exist_ok=True)

shade_classes = {
    0.00: 0, #bldg shade
    0.03: 1, #tree shade
    1.00: 2  #no shade
}

class_labels = ["Building Shade", "Tree Shade", "No Shade"]


def classify_raster(raster_data):
    classified = np.full(raster_data.shape, -1, dtype=np.int8)
    for val, label in shade_classes.items():
        mask = np.isclose(raster_data, val, atol=0.0005)
        classified[mask] = label  
    return classified

#read and classify rasters
with rasterio.open(local_path) as src_local, rasterio.open(global_path) as src_global:
    local_data = classify_raster(src_local.read(1))
    global_data = classify_raster(src_global.read(1))

#flatten and filter
mask = (local_data != -1) & (global_data != -1)
y_true = local_data[mask].flatten()
y_pred = global_data[mask].flatten()

#compute metrics - confusion matrix, kappa score, user&producer accuracy
conf_mat = confusion_matrix(y_true, y_pred, labels=[0,1,2])
kappa = cohen_kappa_score(y_true, y_pred)
user_accuracy = np.diag(conf_mat) / np.sum(conf_mat, axis = 0)
producer_accuracy = np.diag(conf_mat) / np.sum(conf_mat, axis =1)

#save results
conf_df = pd.DataFrame(conf_mat, index=class_labels, columns = class_labels)
conf_df.to_csv(output_dir / f"confusion_matrix_{time}.csv")

acc_df = pd.DataFrame({
    "Class": class_labels,
    "User Accuracy": user_accuracy,
    "Producer Accuracy": producer_accuracy
})

acc_df.to_csv(output_dir / f"shade accuracy_{time}.csv", index = False)

with open(output_dir / f"kappa_{time}.txt", "w") as f:
    f.write(f"Kappa Coefficient: {kappa:.4f}")

print("Shade validation successful.")
print(f"Validation metrics saved to: {output_dir.resolve()}")

# if __name__=="__main__":
#     main()