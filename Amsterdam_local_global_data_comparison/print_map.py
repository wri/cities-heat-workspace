import rasterio
from rasterio.plot import show
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.patches import Rectangle
import contextily as ctx
import numpy as np
import os
from pathlib import Path
from matplotlib.colors import Normalize, LinearSegmentedColormap, ListedColormap, BoundaryNorm, LogNorm, PowerNorm


def create_legend(ax_legend, legend_style, min_val, max_val, cmap=None, norm=None):
    """
    Create a continuous legend for 'temp', 'tree_height', or 'building_height'.

    Parameters:
    - ax_legend: The axes where the legend will be drawn.
    - legend_style: 'temp', 'tree_height', or 'building_height'.
    - min_val: Minimum value of the raster (for continuous legends).
    - max_val: Maximum value of the raster (for continuous legends).
    - cmap: Colormap for continuous legends.
    - norm: Normalization for continuous legends.
    """
    label = {
        "temp": "TMRT (°C)",
        "tree_height": "Tree Height (m)",
        "building_height": "Building Height (m)",
        "utci": "UTCI(°C)"
    }.get(legend_style, "Value")

    colorbar = plt.colorbar(
        plt.cm.ScalarMappable(cmap=cmap, norm=norm),
        cax=ax_legend,
        orientation="vertical"
    )
    colorbar.set_label(label, fontsize=10)
    colorbar.ax.tick_params(labelsize=8)
    colorbar.ax.text(0.5, -0.15, f"{min_val:.1f}", fontsize=8, ha="center", transform=ax_legend.transAxes)
    colorbar.ax.text(0.5, 1.05, f"{max_val:.1f}", fontsize=8, ha="center", transform=ax_legend.transAxes)


def create_map(raster_path, inset_path, legend_style="shade", output_file=None):
    """
    Create a map layout with no margins, an inset map at the top-right, and the legend at the bottom-right.

    Parameters:
    - raster_path: Path to the input raster file.
    - inset_path: Path to the pre-created inset map image file.
    - legend_style: 'shade', 'temp', 'tree_height', or 'building_height', utci, utci_diff_reclass.
    - output_file: Optional. Path to save the map as an image file. If None, the map will only be displayed.
    """
    # Load raster data
    raster = rasterio.open(raster_path)
    raster_bounds = raster.bounds
    raster_extent = [raster_bounds.left, raster_bounds.right, raster_bounds.bottom, raster_bounds.top]
    raster_crs = raster.crs.to_string()

    # Read raster data for legend and analysis
    raster_data = raster.read(1)
    raster_data = np.ma.masked_equal(raster_data, raster.nodata)  # Mask nodata values
    min_val, max_val = raster_data.min(), raster_data.max()

    # if legend_style in ["temp", "tree_height", "building_height"]:
    #     quantiles = np.percentile(raster_data.compressed(), [0, 25, 50, 75, 100])  # Quartiles
    #     cmap = "turbo"  # Blue-to-red color ramp
    #     norm = plt.cm.colors.BoundaryNorm(boundaries=quantiles, ncolors=256)
    # else:
    #     cmap = None
    #     norm = None

    # Set up the figure
    fig = plt.figure(figsize=(9, 6))  # Adjusted for a tight layout
    ax_map = fig.add_axes([-0.04, 0, 0.75, 1])  # Main map occupies the left without margins

    # if legend_style in ["temp", "tree_height", "building_height"]:  # Continuous color ramp
    #     # Use PowerNorm for a nonlinear scaling emphasizing lower values
    #     cmap = LinearSegmentedColormap.from_list(
    #         "TurboEnhanced",
    #         ["#0000FF", "#00FFFF", "#FFFF00", "#FF7F00", "#FF0000"]
    #     )
    #     norm = Normalize(vmin=min_val, vmax=max_val)
    #
    #     # Plot the raster layer with enhanced Turbo colormap
    #     show(raster, ax=ax_map, extent=raster_extent, alpha=1.0, cmap=cmap, norm=norm)

    cmap = None
    norm = None
    if legend_style in ["temp", "tree_height", "building_height", "utci"]:  # Continuous color ramp
        # Use PowerNorm for a nonlinear scaling emphasizing lower values
        norm = PowerNorm(gamma=0.5, vmin=min_val, vmax=max_val)  # Adjust gamma as needed for emphasis
        cmap = "turbo"  # Turbo colormap for smooth blue-to-red transition

        # Debugging: Print range and normalization method
        print(f"Using PowerNorm with gamma=0.5 for {legend_style}")

        # Plot the raster with continuous colormap and PowerNorm scaling
        show(raster, ax=ax_map, extent=raster_extent, alpha=1.0, cmap=cmap, norm=norm)

    elif legend_style == "shade":  # Discrete color ramp for shade
        colors = ["blue", "green", "#FFF2A0"]
        bounds = [-0.5, 0.02, 0.5, 1.5]
        cmap = ListedColormap(colors)
        norm = BoundaryNorm(bounds, cmap.N)
        show(raster, ax=ax_map, extent=raster_extent, alpha=1.0, cmap=cmap, norm=norm)

    elif legend_style == "utci_diff_reclass":

        base_cmap = plt.cm.coolwarm
        color_indices = [1, 30, 70, 99, 140, 175, 220, 250]  # Adjusted for a smooth transition
        colors = base_cmap(color_indices)
        cmap = ListedColormap(colors)
        norm = Normalize(vmin=-6, vmax=6)
        show(raster, ax=ax_map, extent=raster_extent, alpha=1.0, cmap=cmap, norm=norm)

    # Add OpenStreetMap basemap below the raster
    ctx.add_basemap(ax_map, crs=raster_crs, source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.15)

    # Remove axis labels
    ax_map.axis("off")

    # Add a scale bar (200 meters)
    scale_length_m = 200  # Scale bar length in meters
    scale_bar_start = raster_bounds.left + (raster_bounds.right - raster_bounds.left) * 0.05
    scale_bar_end = scale_bar_start + scale_length_m

    # Draw the black-white alternating bar
    scale_bar_y = raster_bounds.bottom + (raster_bounds.top - raster_bounds.bottom) * 0.05
    ax_map.hlines(scale_bar_y, scale_bar_start, scale_bar_start + scale_length_m / 2, color="black", linewidth=8)
    ax_map.hlines(scale_bar_y, scale_bar_start + scale_length_m / 2, scale_bar_end, color="white", linewidth=8)

    # Add scale labels
    ax_map.text(scale_bar_start, scale_bar_y + (raster_bounds.top - raster_bounds.bottom) * 0.02,
                "0 m", fontsize=8, va="center", ha="center")
    ax_map.text(scale_bar_end, scale_bar_y + (raster_bounds.top - raster_bounds.bottom) * 0.02,
                "200 m", fontsize=8, va="center", ha="center")

    # Add inset map
    ax_inset = fig.add_axes([0.67, 0.46, 0.332, 0.56])
    inset_img = plt.imread(inset_path)
    ax_inset.imshow(inset_img)
    ax_inset.axis("off")

    # Add the legend

    if legend_style in ["temp", "tree_height", "building_height", "utci"]:
        ax_legend = fig.add_axes([0.75, 0.08, 0.08, 0.3])  # Continuous legends
        colorbar = plt.colorbar(
            plt.cm.ScalarMappable(cmap=cmap, norm=norm),
            cax=ax_legend,
            orientation="vertical"
        )
        label = {
            "temp": "TMRT (°C)",
            "tree_height": "Tree Height (m)",
            "building_height": "Building Height (m)",
            "utci": "UTCI(°C)"
        }.get(legend_style, "Value")

        colorbar.set_label(label, fontsize=10)
        colorbar.ax.tick_params(labelsize=8)
        colorbar.ax.text(0.5, -0.15, f"{min_val:.1f}", fontsize=8, ha="center", transform=ax_legend.transAxes)
        colorbar.ax.text(0.5, 1.05, f"{max_val:.1f}", fontsize=8, ha="center", transform=ax_legend.transAxes)

    elif legend_style == "shade":
        ax_legend = fig.add_axes([0.75, 0.08, 0.08, 0.3])
        ax_legend.axis("off")
        legend_items = [
            {"label": "Building Shade", "color": "blue"},
            {"label": "Tree Shade", "color": "green"},
            {"label": "No Shade", "color": "#FFF2A0"},
        ]
        for i, item in enumerate(legend_items):
            ax_legend.add_patch(
                plt.Rectangle((0, 0.8 - i * 0.2), 0.2, 0.1, color=item["color"], transform=ax_legend.transAxes))
            ax_legend.text(0.25, 0.85 - i * 0.2, item["label"], transform=ax_legend.transAxes,
                           fontsize=9, va="center", ha="left")

    elif legend_style == "utci_diff_reclass":
        ax_legend = fig.add_axes([0.78, -0.2, 0.1, 0.8])
        unique_values = [-4, -2, -1, 0, 1, 2, 4, 10]
        labels = ["< -4°C", "-4 to -2°C", "-2 to -1°C", "-1 to 0°C", "0 to 1°C", "1 to 2°C", "2 to 4°C", "> 4°C"]
        patches = [Patch(color=cmap(norm(value)), label=label) for value, label in zip(unique_values, labels)]
        legend = ax_legend.legend(handles=patches, loc='center', title="UTCI difference compared with baseline")
        ax_legend.axis('off')

    # Add a proper north arrow in the upper-right corner of the main map
    ax_map.annotate(
        '', xy=(0.9, 0.9), xycoords='axes fraction', xytext=(0.9, 0.8),
        arrowprops=dict(facecolor='black', width=5, headwidth=15, headlength=15)
    )
    ax_map.text(0.9, 0.92, "N", ha="center", va="center", fontsize=14, transform=ax_map.transAxes)

    # Save or show the map
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
    else:
        plt.show()

#create_map(r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile001\source_data\aoi1_tree_height.tif", r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\inset_aoi1.png", legend_style="building_height", output_file= None)
#create_map(r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\utci_reclass\utci_global_diff\difference_15_recl.tif", r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\inset_aoi1.png", legend_style="utci_diff_reclass", output_file= None)
#create_map(r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile001\source_data\UTbuilding_NASADEM_1.tif", r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\inset_aoi1.png", legend_style="building_height", output_file= r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\source_data\global_building.png")
#create_map(r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\Tile001\source_data\UTbuilding_NASADEM_1.tif", r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\inset_aoi1.png", legend_style="building_height")

def batch_process_maps(input_folder, inset_path, output_folder, legend_style="shade"):
    """
    Batch process `.tif` files to create maps with the specified layout.

    Parameters:
    - input_folder: Folder containing `.tif` files.
    - inset_path: Path to the pre-created inset map image file.
    - output_folder: Folder to save the output maps.
    - legend_style: 'shade' for processing Shadow_* files,
                    'temp' for Tmrt_* files,
                    'utci' for UTCI_* files,
                    'utci_diff_reclass' for Difference_* files.
    """
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    if legend_style == "utci_diff_reclass":
        prefix = "difference"
        # Process only files that start with 'difference_'
        for tif_file in Path(input_folder).glob(f"{prefix}_*.tif"):
            output_file = Path(output_folder) / (tif_file.stem + ".png")
            print(f"Processing {tif_file} -> {output_file}")
            create_map(
                raster_path=str(tif_file),
                inset_path=inset_path,
                legend_style=legend_style,
                output_file=str(output_file)
            )
    elif legend_style in ["shade", "temp", "utci"]:
        # Define prefix and time mapping based on legend_style
        if legend_style == "shade":
            prefix = "Shadow"
            time_mapping = {"1200D": "12", "1500D": "15", "1800D": "18", "average": "average"}
        elif legend_style == "temp":
            prefix = "Tmrt"
            time_mapping = {"1200D": "12", "1500D": "15", "1800D": "18", "average": "average"}
        elif legend_style == "utci":
            prefix = "UTCI"
            time_mapping = {"12": "12", "15": "15", "18": "18", "average": "average"}

        # Loop through all `.tif` files matching the prefix in the input folder
        for tif_file in Path(input_folder).glob(f"{prefix}_*.tif"):
            base_name = tif_file.stem
            time_suffix = base_name.split("_")[-1]
            output_time = time_mapping.get(time_suffix, "unknown")

            if output_time == "unknown":
                print(f"Unrecognized time format in file {tif_file}, skipping...")
                continue

            output_file = Path(output_folder) / f"{Path(input_folder).name}_{output_time}.png"
            print(f"Processing {tif_file} -> {output_file}")
            create_map(
                raster_path=str(tif_file),
                inset_path=inset_path,
                legend_style=legend_style,
                output_file=str(output_file)
            )
    else:
        raise ValueError("Invalid legend_style. Choose 'shade', 'temp', 'utci', or 'utci_diff_reclass'.")

# Example usage
# batch_process_maps(
#     input_folder=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_results\aoi1_all_local_auto",  # Folder containing .tif files
#     inset_path=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\inset_aoi1.png",  # Path to inset map image
#     output_folder=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\tmrt_local",  # Folder to save output maps
#     legend_style="temp"  # Or "temp" for a continuous legend
# )


# # Example usage
# create_map(
#     raster_path=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_results\aoi1_all_global\Shadow_2023_189_1200D.tif",
#     inset_path=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\inset_aoi1.png",  # Provide your inset map here
#     legend_style="shade",
#     output_file=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\aoi1_all_global.png"
# )

# Example usage
# batch_process_maps(
#     input_folder=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_utci\aoi1_all_local_auto",  # Folder containing .tif files
#     inset_path=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\inset_aoi1.png",  # Path to inset map image
#     output_folder=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\utci_local",  # Folder to save output maps
#     legend_style="utci"  # Or "temp" for a continuous legend
# )
#output_file= r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\all_global_shadow_12.tif",

if __name__ == '__main__':
    batch_process_maps(
        input_folder=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\utci_reclass\utci_global_diff_aggr",
        # Folder containing .tif files
        inset_path=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\inset_aoi1.png",
        # Path to inset map image
        output_folder=r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\print_maps\utci_reclass\utci_global_diff_aggr",
        # Folder to save output maps
        legend_style="utci_diff_reclass"  # Or "temp" for a continuous legend
    )

C:\Users\zhuoyue.wang\Documents\Amsterdam_data\aoi2_street_tree_utci_diff