import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.coords import BoundingBox
from rasterio.warp import transform_bounds
from sklearn.metrics import confusion_matrix, cohen_kappa_score
import pandas as pd
from pathlib import Path

# File root and pattern
base_time_steps = ["1200D", "1500D", "1800D"]
city = "Monterrey"

global_base = "/Users/hyejijoh/Documents/wri_proj/Monterrey/data/ctcm/global/output/Shadow_2023_172_{}.tif"
local_base = "/Users/hyejijoh/Downloads/Shadow_2023_172_{}.tif"

# Output directory
output_dir = Path("results/shade")
output_dir.mkdir(parents=True, exist_ok=True)

# Classification scheme
shade_classes = {
    0.00: 0,
    0.03: 1,
    1.00: 2
}
class_labels = ["Building Shade", "Tree Shade", "No Shade"]

def classify_raster(data):
    classified = np.full(data.shape, -1, dtype=np.int8)
    for val, label in shade_classes.items():
        mask = np.isclose(data, val, atol=0.0005)
        classified[mask] = label
    return classified

def get_overlap_window(src1, src2):
    if src1.crs != src2.crs:
        bounds2 = transform_bounds(src2.crs, src1.crs, *src2.bounds)
    else:
        bounds2 = src2.bounds

    overlap_bounds = BoundingBox(
        max(src1.bounds.left, bounds2.left),
        max(src1.bounds.bottom, bounds2.bottom),
        min(src1.bounds.right, bounds2.right),
        min(src1.bounds.top, bounds2.top)
    )

    if (overlap_bounds.right <= overlap_bounds.left) or (overlap_bounds.top <= overlap_bounds.bottom):
        raise ValueError("No overlapping region between rasters.")

    window1 = from_bounds(*overlap_bounds, transform=src1.transform)
    window2 = from_bounds(*overlap_bounds, transform=src2.transform)
    return window1.round_offsets(), window2.round_offsets()

# Storage for results
kappa_results = []
accuracy_results = []
confusion_results = []

# Run for each time step
for time in base_time_steps:
    global_path = global_base.format(time)
    local_path = local_base.format(time)

    with rasterio.open(local_path) as src_local, rasterio.open(global_path) as src_global:
        if src_local.crs != src_global.crs:
            raise ValueError("CRS mismatch. Reproject manually before validation.")

        if src_local.transform != src_global.transform or src_local.shape != src_global.shape or src_local.bounds != src_global.bounds:
            print(f"🟠 {time}: Raster mismatch detected. Cropping.")
            win_local, win_global = get_overlap_window(src_local, src_global)
            local_data = classify_raster(src_local.read(1, window=win_local))
            global_data = classify_raster(src_global.read(1, window=win_global))
        else:
            print(f"🟢 {time}: Rasters aligned. Proceeding.")
            local_data = classify_raster(src_local.read(1))
            global_data = classify_raster(src_global.read(1))

    mask = (local_data != -1) & (global_data != -1)
    y_true = local_data[mask].flatten()
    y_pred = global_data[mask].flatten()

    conf_mat = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
    kappa = cohen_kappa_score(y_true, y_pred)
    user_accuracy = np.diag(conf_mat) / np.sum(conf_mat, axis=0)
    producer_accuracy = np.diag(conf_mat) / np.sum(conf_mat, axis=1)

    # Store metrics
    kappa_results.append({"Time": time, "Kappa Coefficient": kappa})
    for i, label in enumerate(class_labels):
        accuracy_results.append({
            "Time": time,
            "Class": label,
            "User Accuracy": user_accuracy[i],
            "Producer Accuracy": producer_accuracy[i]
        })

    flat_conf = conf_mat.flatten()
    for i, row_label in enumerate(class_labels):
        for j, col_label in enumerate(class_labels):
            confusion_results.append({
                "Time": time,
                "Actual Class": row_label,
                "Predicted Class": col_label,
                "Count": conf_mat[i, j]
            })

# Save all outputs
pd.DataFrame(kappa_results).to_csv(output_dir / "shade_kappa_all.txt", index=False)
pd.DataFrame(accuracy_results).to_csv(output_dir / "shade_accuracy_all.csv", index=False)
pd.DataFrame(confusion_results).to_csv(output_dir / "shade_confusion_matrix_all.csv", index=False)

print("✅ All shade validations complete.")
print(f"Results saved to: {output_dir.resolve()}")