import os
import rasterio
import numpy as np
import pandas as pd
from shade_area_calculation import read_raster, get_bbx_with_edge_buffer, crop_to_bbx


def utci_calc(Ta, ehPa, va, Tmrt):
    # eOUBLE PRECISION Function value is the UTCI in degree Celsius
    # computed by a 6th order approximating polynomial from the 4 Input paramters
    # Input parameters (all of type double precision)
    # 	- Ta : air temperature, degree Celsius
    # 	- ehPa : water vapour presure, hPa=hecto Pascal
    # 	- va : wind speed 10 m above ground level in m/s
    # 	- Tmrt : mean radiant temperature, degree Celsius

    # UTCI_approx, Version a 0.002, October 2009
    # Copyright (C) 2009  Peter Broede

    '''returns a nunpy array'''

    D_Tmrt = Tmrt - Ta
    # use vapour pressure in kPa
    Pa = ehPa / 10.0
    # calculate 6th order polynomial as approximation
    UTCI_approx = [Ta +
                   (6.07562052e-01) +
                   (-2.27712343e-02) * Ta +
                   (8.06470249e-04) * Ta * Ta +
                   (-1.54271372e-04) * Ta * Ta * Ta +
                   (-3.24651735e-06) * Ta * Ta * Ta * Ta +
                   (7.32602852e-08) * Ta * Ta * Ta * Ta * Ta +
                   (1.35959073e-09) * Ta * Ta * Ta * Ta * Ta * Ta +
                   (-2.25836520e+00) * va +
                   (8.80326035e-02) * Ta * va +
                   (2.16844454e-03) * Ta * Ta * va +
                   (-1.53347087e-05) * Ta * Ta * Ta * va +
                   (-5.72983704e-07) * Ta * Ta * Ta * Ta * va +
                   (-2.55090145e-09) * Ta * Ta * Ta * Ta * Ta * va +
                   (-7.51269505e-01) * va * va +
                   (-4.08350271e-03) * Ta * va * va +
                   (-5.21670675e-05) * Ta * Ta * va * va +
                   (1.94544667e-06) * Ta * Ta * Ta * va * va +
                   (1.14099531e-08) * Ta * Ta * Ta * Ta * va * va +
                   (1.58137256e-01) * va * va * va +
                   (-6.57263143e-05) * Ta * va * va * va +
                   (2.22697524e-07) * Ta * Ta * va * va * va +
                   (-4.16117031e-08) * Ta * Ta * Ta * va * va * va +
                   (-1.27762753e-02) * va * va * va * va +
                   (9.66891875e-06) * Ta * va * va * va * va +
                   (2.52785852e-09) * Ta * Ta * va * va * va * va +
                   (4.56306672e-04) * va * va * va * va * va +
                   (-1.74202546e-07) * Ta * va * va * va * va * va +
                   (-5.91491269e-06) * va * va * va * va * va * va +
                   (3.98374029e-01) * D_Tmrt +
                   (1.83945314e-04) * Ta * D_Tmrt +
                   (-1.73754510e-04) * Ta * Ta * D_Tmrt +
                   (-7.60781159e-07) * Ta * Ta * Ta * D_Tmrt +
                   (3.77830287e-08) * Ta * Ta * Ta * Ta * D_Tmrt +
                   (5.43079673e-10) * Ta * Ta * Ta * Ta * Ta * D_Tmrt +
                   (-2.00518269e-02) * va * D_Tmrt +
                   (8.92859837e-04) * Ta * va * D_Tmrt +
                   (3.45433048e-06) * Ta * Ta * va * D_Tmrt +
                   (-3.77925774e-07) * Ta * Ta * Ta * va * D_Tmrt +
                   (-1.69699377e-09) * Ta * Ta * Ta * Ta * va * D_Tmrt +
                   (1.69992415e-04) * va * va * D_Tmrt +
                   (-4.99204314e-05) * Ta * va * va * D_Tmrt +
                   (2.47417178e-07) * Ta * Ta * va * va * D_Tmrt +
                   (1.07596466e-08) * Ta * Ta * Ta * va * va * D_Tmrt +
                   (8.49242932e-05) * va * va * va * D_Tmrt +
                   (1.35191328e-06) * Ta * va * va * va * D_Tmrt +
                   (-6.21531254e-09) * Ta * Ta * va * va * va * D_Tmrt +
                   (-4.99410301e-06) * va * va * va * va * D_Tmrt +
                   (-1.89489258e-08) * Ta * va * va * va * va * D_Tmrt +
                   (8.15300114e-08) * va * va * va * va * va * D_Tmrt +
                   (7.55043090e-04) * D_Tmrt * D_Tmrt +
                   (-5.65095215e-05) * Ta * D_Tmrt * D_Tmrt +
                   (-4.52166564e-07) * Ta * Ta * D_Tmrt * D_Tmrt +
                   (2.46688878e-08) * Ta * Ta * Ta * D_Tmrt * D_Tmrt +
                   (2.42674348e-10) * Ta * Ta * Ta * Ta * D_Tmrt * D_Tmrt +
                   (1.54547250e-04) * va * D_Tmrt * D_Tmrt +
                   (5.24110970e-06) * Ta * va * D_Tmrt * D_Tmrt +
                   (-8.75874982e-08) * Ta * Ta * va * D_Tmrt * D_Tmrt +
                   (-1.50743064e-09) * Ta * Ta * Ta * va * D_Tmrt * D_Tmrt +
                   (-1.56236307e-05) * va * va * D_Tmrt * D_Tmrt +
                   (-1.33895614e-07) * Ta * va * va * D_Tmrt * D_Tmrt +
                   (2.49709824e-09) * Ta * Ta * va * va * D_Tmrt * D_Tmrt +
                   (6.51711721e-07) * va * va * va * D_Tmrt * D_Tmrt +
                   (1.94960053e-09) * Ta * va * va * va * D_Tmrt * D_Tmrt +
                   (-1.00361113e-08) * va * va * va * va * D_Tmrt * D_Tmrt +
                   (-1.21206673e-05) * D_Tmrt * D_Tmrt * D_Tmrt +
                   (-2.18203660e-07) * Ta * D_Tmrt * D_Tmrt * D_Tmrt +
                   (7.51269482e-09) * Ta * Ta * D_Tmrt * D_Tmrt * D_Tmrt +
                   (9.79063848e-11) * Ta * Ta * Ta * D_Tmrt * D_Tmrt * D_Tmrt +
                   (1.25006734e-06) * va * D_Tmrt * D_Tmrt * D_Tmrt +
                   (-1.81584736e-09) * Ta * va * D_Tmrt * D_Tmrt * D_Tmrt +
                   (-3.52197671e-10) * Ta * Ta * va * D_Tmrt * D_Tmrt * D_Tmrt +
                   (-3.36514630e-08) * va * va * D_Tmrt * D_Tmrt * D_Tmrt +
                   (1.35908359e-10) * Ta * va * va * D_Tmrt * D_Tmrt * D_Tmrt +
                   (4.17032620e-10) * va * va * va * D_Tmrt * D_Tmrt * D_Tmrt +
                   (-1.30369025e-09) * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt +
                   (4.13908461e-10) * Ta * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt +
                   (9.22652254e-12) * Ta * Ta * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt +
                   (-5.08220384e-09) * va * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt +
                   (-2.24730961e-11) * Ta * va * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt +
                   (1.17139133e-10) * va * va * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt +
                   (6.62154879e-10) * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt +
                   (4.03863260e-13) * Ta * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt +
                   (1.95087203e-12) * va * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt +
                   (-4.73602469e-12) * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt +
                   (5.12733497e+00) * Pa +
                   (-3.12788561e-01) * Ta * Pa +
                   (-1.96701861e-02) * Ta * Ta * Pa +
                   (9.99690870e-04) * Ta * Ta * Ta * Pa +
                   (9.51738512e-06) * Ta * Ta * Ta * Ta * Pa +
                   (-4.66426341e-07) * Ta * Ta * Ta * Ta * Ta * Pa +
                   (5.48050612e-01) * va * Pa +
                   (-3.30552823e-03) * Ta * va * Pa +
                   (-1.64119440e-03) * Ta * Ta * va * Pa +
                   (-5.16670694e-06) * Ta * Ta * Ta * va * Pa +
                   (9.52692432e-07) * Ta * Ta * Ta * Ta * va * Pa +
                   (-4.29223622e-02) * va * va * Pa +
                   (5.00845667e-03) * Ta * va * va * Pa +
                   (1.00601257e-06) * Ta * Ta * va * va * Pa +
                   (-1.81748644e-06) * Ta * Ta * Ta * va * va * Pa +
                   (-1.25813502e-03) * va * va * va * Pa +
                   (-1.79330391e-04) * Ta * va * va * va * Pa +
                   (2.34994441e-06) * Ta * Ta * va * va * va * Pa +
                   (1.29735808e-04) * va * va * va * va * Pa +
                   (1.29064870e-06) * Ta * va * va * va * va * Pa +
                   (-2.28558686e-06) * va * va * va * va * va * Pa +
                   (-3.69476348e-02) * D_Tmrt * Pa +
                   (1.62325322e-03) * Ta * D_Tmrt * Pa +
                   (-3.14279680e-05) * Ta * Ta * D_Tmrt * Pa +
                   (2.59835559e-06) * Ta * Ta * Ta * D_Tmrt * Pa +
                   (-4.77136523e-08) * Ta * Ta * Ta * Ta * D_Tmrt * Pa +
                   (8.64203390e-03) * va * D_Tmrt * Pa +
                   (-6.87405181e-04) * Ta * va * D_Tmrt * Pa +
                   (-9.13863872e-06) * Ta * Ta * va * D_Tmrt * Pa +
                   (5.15916806e-07) * Ta * Ta * Ta * va * D_Tmrt * Pa +
                   (-3.59217476e-05) * va * va * D_Tmrt * Pa +
                   (3.28696511e-05) * Ta * va * va * D_Tmrt * Pa +
                   (-7.10542454e-07) * Ta * Ta * va * va * D_Tmrt * Pa +
                   (-1.24382300e-05) * va * va * va * D_Tmrt * Pa +
                   (-7.38584400e-09) * Ta * va * va * va * D_Tmrt * Pa +
                   (2.20609296e-07) * va * va * va * va * D_Tmrt * Pa +
                   (-7.32469180e-04) * D_Tmrt * D_Tmrt * Pa +
                   (-1.87381964e-05) * Ta * D_Tmrt * D_Tmrt * Pa +
                   (4.80925239e-06) * Ta * Ta * D_Tmrt * D_Tmrt * Pa +
                   (-8.75492040e-08) * Ta * Ta * Ta * D_Tmrt * D_Tmrt * Pa +
                   (2.77862930e-05) * va * D_Tmrt * D_Tmrt * Pa +
                   (-5.06004592e-06) * Ta * va * D_Tmrt * D_Tmrt * Pa +
                   (1.14325367e-07) * Ta * Ta * va * D_Tmrt * D_Tmrt * Pa +
                   (2.53016723e-06) * va * va * D_Tmrt * D_Tmrt * Pa +
                   (-1.72857035e-08) * Ta * va * va * D_Tmrt * D_Tmrt * Pa +
                   (-3.95079398e-08) * va * va * va * D_Tmrt * D_Tmrt * Pa +
                   (-3.59413173e-07) * D_Tmrt * D_Tmrt * D_Tmrt * Pa +
                   (7.04388046e-07) * Ta * D_Tmrt * D_Tmrt * D_Tmrt * Pa +
                   (-1.89309167e-08) * Ta * Ta * D_Tmrt * D_Tmrt * D_Tmrt * Pa +
                   (-4.79768731e-07) * va * D_Tmrt * D_Tmrt * D_Tmrt * Pa +
                   (7.96079978e-09) * Ta * va * D_Tmrt * D_Tmrt * D_Tmrt * Pa +
                   (1.62897058e-09) * va * va * D_Tmrt * D_Tmrt * D_Tmrt * Pa +
                   (3.94367674e-08) * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt * Pa +
                   (-1.18566247e-09) * Ta * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt * Pa +
                   (3.34678041e-10) * va * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt * Pa +
                   (-1.15606447e-10) * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt * Pa +
                   (-2.80626406e+00) * Pa * Pa +
                   (5.48712484e-01) * Ta * Pa * Pa +
                   (-3.99428410e-03) * Ta * Ta * Pa * Pa +
                   (-9.54009191e-04) * Ta * Ta * Ta * Pa * Pa +
                   (1.93090978e-05) * Ta * Ta * Ta * Ta * Pa * Pa +
                   (-3.08806365e-01) * va * Pa * Pa +
                   (1.16952364e-02) * Ta * va * Pa * Pa +
                   (4.95271903e-04) * Ta * Ta * va * Pa * Pa +
                   (-1.90710882e-05) * Ta * Ta * Ta * va * Pa * Pa +
                   (2.10787756e-03) * va * va * Pa * Pa +
                   (-6.98445738e-04) * Ta * va * va * Pa * Pa +
                   (2.30109073e-05) * Ta * Ta * va * va * Pa * Pa +
                   (4.17856590e-04) * va * va * va * Pa * Pa +
                   (-1.27043871e-05) * Ta * va * va * va * Pa * Pa +
                   (-3.04620472e-06) * va * va * va * va * Pa * Pa +
                   (5.14507424e-02) * D_Tmrt * Pa * Pa +
                   (-4.32510997e-03) * Ta * D_Tmrt * Pa * Pa +
                   (8.99281156e-05) * Ta * Ta * D_Tmrt * Pa * Pa +
                   (-7.14663943e-07) * Ta * Ta * Ta * D_Tmrt * Pa * Pa +
                   (-2.66016305e-04) * va * D_Tmrt * Pa * Pa +
                   (2.63789586e-04) * Ta * va * D_Tmrt * Pa * Pa +
                   (-7.01199003e-06) * Ta * Ta * va * D_Tmrt * Pa * Pa +
                   (-1.06823306e-04) * va * va * D_Tmrt * Pa * Pa +
                   (3.61341136e-06) * Ta * va * va * D_Tmrt * Pa * Pa +
                   (2.29748967e-07) * va * va * va * D_Tmrt * Pa * Pa +
                   (3.04788893e-04) * D_Tmrt * D_Tmrt * Pa * Pa +
                   (-6.42070836e-05) * Ta * D_Tmrt * D_Tmrt * Pa * Pa +
                   (1.16257971e-06) * Ta * Ta * D_Tmrt * D_Tmrt * Pa * Pa +
                   (7.68023384e-06) * va * D_Tmrt * D_Tmrt * Pa * Pa +
                   (-5.47446896e-07) * Ta * va * D_Tmrt * D_Tmrt * Pa * Pa +
                   (-3.59937910e-08) * va * va * D_Tmrt * D_Tmrt * Pa * Pa +
                   (-4.36497725e-06) * D_Tmrt * D_Tmrt * D_Tmrt * Pa * Pa +
                   (1.68737969e-07) * Ta * D_Tmrt * D_Tmrt * D_Tmrt * Pa * Pa +
                   (2.67489271e-08) * va * D_Tmrt * D_Tmrt * D_Tmrt * Pa * Pa +
                   (3.23926897e-09) * D_Tmrt * D_Tmrt * D_Tmrt * D_Tmrt * Pa * Pa +
                   (-3.53874123e-02) * Pa * Pa * Pa +
                   (-2.21201190e-01) * Ta * Pa * Pa * Pa +
                   (1.55126038e-02) * Ta * Ta * Pa * Pa * Pa +
                   (-2.63917279e-04) * Ta * Ta * Ta * Pa * Pa * Pa +
                   (4.53433455e-02) * va * Pa * Pa * Pa +
                   (-4.32943862e-03) * Ta * va * Pa * Pa * Pa +
                   (1.45389826e-04) * Ta * Ta * va * Pa * Pa * Pa +
                   (2.17508610e-04) * va * va * Pa * Pa * Pa +
                   (-6.66724702e-05) * Ta * va * va * Pa * Pa * Pa +
                   (3.33217140e-05) * va * va * va * Pa * Pa * Pa +
                   (-2.26921615e-03) * D_Tmrt * Pa * Pa * Pa +
                   (3.80261982e-04) * Ta * D_Tmrt * Pa * Pa * Pa +
                   (-5.45314314e-09) * Ta * Ta * D_Tmrt * Pa * Pa * Pa +
                   (-7.96355448e-04) * va * D_Tmrt * Pa * Pa * Pa +
                   (2.53458034e-05) * Ta * va * D_Tmrt * Pa * Pa * Pa +
                   (-6.31223658e-06) * va * va * D_Tmrt * Pa * Pa * Pa +
                   (3.02122035e-04) * D_Tmrt * D_Tmrt * Pa * Pa * Pa +
                   (-4.77403547e-06) * Ta * D_Tmrt * D_Tmrt * Pa * Pa * Pa +
                   (1.73825715e-06) * va * D_Tmrt * D_Tmrt * Pa * Pa * Pa +
                   (-4.09087898e-07) * D_Tmrt * D_Tmrt * D_Tmrt * Pa * Pa * Pa +
                   (6.14155345e-01) * Pa * Pa * Pa * Pa +
                   (-6.16755931e-02) * Ta * Pa * Pa * Pa * Pa +
                   (1.33374846e-03) * Ta * Ta * Pa * Pa * Pa * Pa +
                   (3.55375387e-03) * va * Pa * Pa * Pa * Pa +
                   (-5.13027851e-04) * Ta * va * Pa * Pa * Pa * Pa +
                   (1.02449757e-04) * va * va * Pa * Pa * Pa * Pa +
                   (-1.48526421e-03) * D_Tmrt * Pa * Pa * Pa * Pa +
                   (-4.11469183e-05) * Ta * D_Tmrt * Pa * Pa * Pa * Pa +
                   (-6.80434415e-06) * va * D_Tmrt * Pa * Pa * Pa * Pa +
                   (-9.77675906e-06) * D_Tmrt * D_Tmrt * Pa * Pa * Pa * Pa +
                   (8.82773108e-02) * Pa * Pa * Pa * Pa * Pa +
                   (-3.01859306e-03) * Ta * Pa * Pa * Pa * Pa * Pa +
                   (1.04452989e-03) * va * Pa * Pa * Pa * Pa * Pa +
                   (2.47090539e-04) * D_Tmrt * Pa * Pa * Pa * Pa * Pa +
                   (1.48348065e-03) * Pa * Pa * Pa * Pa * Pa * Pa
                   ]

    return np.array(UTCI_approx)

def parse_met_data(met_file):
    """Parse meteorological data from fixed-column format."""
    # Define column names based on the format provided
    col_names = [
        "iy", "id", "it", "imin", "qn", "qh", "qe", "qs", "qf",
        "U", "RH", "Tair", "press", "rain", "kdown", "snow", "ldown",
        "fcld", "wuh", "xsmd", "lai", "kdiff", "kdir", "wdir" ,"vpd"
    ]

    # Read the file with fixed-width format
    df = pd.read_csv(
        met_file,
        delim_whitespace=True,  # Columns are separated by spaces
        names=col_names,        # Specify column names
        na_values="-999",       # Treat "-999" as NaN (this works without a list)
        skiprows=1              # Skip header row if necessary
    )

    return df

def match_met_to_time(met_data, target_time):
    """Match meteorological data to a specific time."""
    matched = met_data[met_data["it"] == target_time]
    if matched.empty:
        raise ValueError(f"No meteorological data found for time {target_time}.")
    return matched.iloc[0]

def check_inputs(at, wind, vpd, mrt_arr):
    """Validate the ranges of meteorological and MRT input values."""
    if not -50 <= at <= 50:
        raise ValueError("Temperature must be between -50 and 50 °C!")
    if not 0.5 <= wind <= 17:
        raise ValueError("Wind speed must be between 0.5 and 17 m/s!")
    if not 0 <= vpd <= 50:
        raise ValueError("Vapor pressure deficit must be between 0 and 50 hPa!")
    if not all((at - 30) <= val <= (at + 70) for val in np.ndarray.flatten(mrt_arr)):
        raise ValueError("MRT must be between 30 °C below and 70 °C above the air temp!")

def calculate_ehPa(T, vpd):
    """
    Calculate water vapor pressure (ehPa) from air temperature (T) and vapor pressure deficit (vpd).

    Parameters:
        T (float): Air temperature in °C.
        vpd (float): Vapor pressure deficit in hPa.

    Returns:
        float: Water vapor pressure (ehPa) in hPa.
    """
    # Calculate saturation vapor pressure (es) in hPa
    es = 6.1078 * (10 ** ((7.5 * T) / (T + 237.3)))
    # Calculate ehPa
    ehPa = es - vpd
    return ehPa


def write_raster(file_path, array, profile):
    """Write array to a raster file using Rasterio."""
    # Ensure array is 2D
    if array.ndim == 3 and array.shape[0] == 1:
        array = array.squeeze(axis=0)

    # Update profile to match array dimensions
    profile.update(
        dtype=rasterio.float32,
        count=1,  # Ensure single band
        height=array.shape[0],
        width=array.shape[1]
    )

    os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Ensure output dir exists
    with rasterio.open(file_path, "w", **profile) as dst:
        dst.write(array, 1)


def process_tmrt_to_utci(main_folder, output_folder, met_file, edge_buffer=500):
    """
    Process Tmrt maps, convert to UTCI, and save UTCI maps while matching meteorological data.

    Parameters:
        main_folder (str): Path to the main folder containing subfolders with Tmrt maps.
        output_folder (str): Path to save the UTCI maps.
        met_file (str): Path to the meteorological data file.
        edge_buffer (int): Buffer distance (in meters) to crop from each edge.

    Returns:
        None
    """
    # Parse meteorological data
    met_data = parse_met_data(met_file)

    # Keys to locate time-of-day Tmrt maps and match them with meteorological data
    time_keys = ["Tmrt_2023_189_1200D", "Tmrt_2023_189_1500D", "Tmrt_2023_189_1800D"]
    time_mapping = {"Tmrt_2023_189_1200D": 12, "Tmrt_2023_189_1500D": 15, "Tmrt_2023_189_1800D": 18}

    # Walk through the main directory
    for subfolder in os.listdir(main_folder):
        subfolder_path = os.path.join(main_folder, subfolder)
        if not os.path.isdir(subfolder_path):
            continue

        print(f"Processing UTCI for run: {subfolder}")
        output_subfolder = os.path.join(output_folder, subfolder)
        os.makedirs(output_subfolder, exist_ok=True)

        # Process each time-of-day map
        for time_key, target_time in time_mapping.items():
            tmrt_file_path = os.path.join(subfolder_path, f"{time_key}.tif")

            if not os.path.exists(tmrt_file_path):
                print(f"Missing file for {time_key} in {subfolder}, skipping...")
                continue

            # Match meteorological data for the specific time
            met_row = match_met_to_time(met_data, target_time)
            at = met_row["Tair"]
            wind = met_row["U"]
            vpd = met_row["vpd"]

            ehPa = calculate_ehPa(at, vpd)

            # Read Tmrt raster
            tmrt_data, tmrt_metadata = read_raster(tmrt_file_path)

            bbx = get_bbx_with_edge_buffer(tmrt_metadata, edge_buffer=edge_buffer)

            # # Calculate the bounding box with edge_buffer
            # from rasterio.transform import array_bounds
            # bounds = array_bounds(
            #     tmrt_metadata['height'],
            #     tmrt_metadata['width'],
            #     tmrt_metadata['transform']
            # )

            # Validate and crop Tmrt raster
            cropped_tmrt, cropped_metadata = crop_to_bbx(tmrt_data, tmrt_metadata, bbx)

            # Validate inputs
            check_inputs(at, wind, vpd, cropped_tmrt)

            # Calculate UTCI
            utci_data = utci_calc(at, ehPa, wind, cropped_tmrt)

            # Save UTCI raster
            output_file = os.path.join(output_subfolder, f"UTCI_{target_time:02d}.tif")
            write_raster(output_file, utci_data.astype(np.float32), cropped_metadata)
            print(f"Saved UTCI raster: {output_file}")


if __name__ == "__main__":
    # Define input/output directories and meteorological data file
    input_main_dir = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_results"
    output_main_dir = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\aoi1_utci_full"
    met_file = r"C:\Users\zhuoyue.wang\Documents\Amsterdam_data\Solweig_AMS\met_era5_hottest_days - Copy.txt"

    # Execute processing
    process_tmrt_to_utci(input_main_dir, output_main_dir, met_file,edge_buffer=0)