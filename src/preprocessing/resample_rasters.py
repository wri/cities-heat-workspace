import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject
from pathlib import Path
import yaml

def resample_raster(input_path, output_path, target_resolution=20, resampling_method=Resampling.average):
    """
    Resample a raster to a target resolution
    
    Args:
        input_path: Path to input raster
        output_path: Path to output resampled raster
        target_resolution: Target resolution in meters (default: 20)
        resampling_method: Resampling method (default: average for continuous data)
    """
    try:
        # Check if input file exists
        if not Path(input_path).exists():
            print(f"❌ Input file not found: {input_path}")
            return False
        
        # Check if output already exists and skip if so
        if Path(output_path).exists():
            print(f"⏭️  Skipping {output_path} (already exists)")
            return True
        
        with rasterio.open(input_path) as src:
            # Get original resolution for logging
            original_res = abs(src.transform.a)
            
            # Calculate new transform and dimensions
            transform, width, height = calculate_default_transform(
                src.crs, src.crs, src.width, src.height, *src.bounds,
                resolution=target_resolution
            )
            
            # Update profile for output
            profile = src.profile.copy()
            profile.update({
                'transform': transform,
                'width': width,
                'height': height
            })
            
            # Create output directory if it doesn't exist
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Create output raster
            with rasterio.open(output_path, 'w', **profile) as dst:
                # Resample each band
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=src.crs,
                        resampling=resampling_method
                    )
        
        print(f"✅ Resampled {Path(input_path).name}: {original_res:.1f}m → {target_resolution}m")
        return True
        
    except Exception as e:
        print(f"❌ Error resampling {input_path}: {e}")
        return False

def resample_shade_data(input_path, output_path, target_resolution=20):
    """
    Resample shade data using nearest neighbor (for categorical data)
    """
    resample_raster(input_path, output_path, target_resolution, Resampling.nearest)

def resample_utci_data(input_path, output_path, target_resolution=20):
    """
    Resample UTCI data using average (for continuous data)
    """
    resample_raster(input_path, output_path, target_resolution, Resampling.average)

def resample_mask_data(input_path, output_path, target_resolution=20):
    """
    Resample mask data using nearest neighbor (for binary data)
    """
    resample_raster(input_path, output_path, target_resolution, Resampling.nearest)

def resample_city_data(city_name, config, file_list, target_resolution=20, force_overwrite=False):
    """Resample all raster data for a specific city"""
    print(f"Resampling rasters for {city_name} to {target_resolution}m resolution")
    print(f"Processing {len(file_list)} files...")
    
    # Process each file
    for file_info in file_list:
        input_path = file_info['input_path']
        output_path = file_info['output_path']
        data_type = file_info['data_type']
        
        if force_overwrite and output_path.exists():
            output_path.unlink()
        
        # Choose resampling method based on data type
        if data_type == 'shade':
            resample_shade_data(input_path, output_path, target_resolution)
        elif data_type == 'utci':
            resample_utci_data(input_path, output_path, target_resolution)
        elif data_type == 'mask':
            resample_mask_data(input_path, output_path, target_resolution)
        else:
            print(f"❌ Unknown data type: {data_type}")


# handles all file structures here1
def main():
    """Main function - choose cities to resample to 20m resolution"""
    # Load configuration
    try:
        with open("config/city_config.yaml", "r") as f:
            all_configs = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Configuration file not found: config/city_config.yaml")
        return
    except yaml.YAMLError as e:
        print(f"❌ Error parsing YAML config: {e}")
        return
    
    # Show available cities
    available_cities = list(all_configs.keys())
    print("Available cities:")
    for i, city in enumerate(available_cities, 1):
        print(f"  {i}. {city}")
    
    # Get user choice
    print("\nChoose cities to resample:")
    print("  - Enter city numbers separated by spaces (e.g., '1 2')")
    print("  - Enter 'all' to process all cities")
    print("  - Enter city names directly (e.g., 'Monterrey1 RiodeJaneiro')")
    
    user_input = input("Your choice: ").strip()
    
    # Parse user input
    if user_input.lower() == 'all':
        cities_to_process = available_cities
    elif user_input.replace(' ', '').isdigit() or any(c.isdigit() for c in user_input.split()):
        # Handle numeric input
        try:
            numbers = [int(x) for x in user_input.split() if x.isdigit()]
            cities_to_process = [available_cities[i-1] for i in numbers if 1 <= i <= len(available_cities)]
        except (ValueError, IndexError):
            print("❌ Invalid numbers. Please try again.")
            return
    else:
        # Handle city names
        cities_to_process = [city.strip() for city in user_input.split()]
    
    if not cities_to_process:
        print("❌ No cities selected.")
        return
    
    # Validate selected cities
    invalid_cities = [city for city in cities_to_process if city not in available_cities]
    if invalid_cities:
        print(f"❌ Invalid cities: {invalid_cities}")
        print(f"Available cities: {available_cities}")
        return
    
    # Process cities at 20m resolution
    resolution = 20
    print(f"\nStarting resampling for {len(cities_to_process)} city(ies) at {resolution}m resolution")
    
    for i, city_name in enumerate(cities_to_process, 1):
        if len(cities_to_process) > 1:
            print(f"\n{'='*60}")
            print(f"Processing city {i}/{len(cities_to_process)}: {city_name}")
            print(f"{'='*60}")
        
        config = {"city": city_name, **all_configs[city_name]}
        
        # Create well-structured output directories
        output_base = Path(f"data/resampled/{city_name}")
        directories = {
            'shade': {
                'local': output_base / "shade" / "local",
                'global': output_base / "shade" / "global"
            },
            'utci': {
                'local': output_base / "utci" / "local", 
                'global': output_base / "utci" / "global"
            },
            'masks': output_base / "masks"
        }
        
        # Create all directories
        for category, paths in directories.items():
            if isinstance(paths, dict):
                for subdir in paths.values():
                    subdir.mkdir(parents=True, exist_ok=True)
            else:
                paths.mkdir(parents=True, exist_ok=True)
        
        print(f"Output directory: {output_base}")
        
        # Build file list for processing
        file_list = []
        
        # Add shade data files
        for shade_path in config.get('shade_local_paths', []):
            input_path = Path(shade_path)
            output_path = directories['shade']['local'] / f"{input_path.stem}_{resolution}m{input_path.suffix}"
            file_list.append({
                'input_path': input_path,
                'output_path': output_path,
                'data_type': 'shade'
            })
        
        for shade_path in config.get('shade_global_paths', []):
            input_path = Path(shade_path)
            output_path = directories['shade']['global'] / f"{input_path.stem}_{resolution}m{input_path.suffix}"
            file_list.append({
                'input_path': input_path,
                'output_path': output_path,
                'data_type': 'shade'
            })
        
        # Add UTCI data files
        for utci_path in config.get('utci_local_paths', []):
            input_path = Path(utci_path)
            output_path = directories['utci']['local'] / f"{input_path.stem}_{resolution}m{input_path.suffix}"
            file_list.append({
                'input_path': input_path,
                'output_path': output_path,
                'data_type': 'utci'
            })
        
        for utci_path in config.get('utci_global_paths', []):
            input_path = Path(utci_path)
            output_path = directories['utci']['global'] / f"{input_path.stem}_{resolution}m{input_path.suffix}"
            file_list.append({
                'input_path': input_path,
                'output_path': output_path,
                'data_type': 'utci'
            })
        
        # Add mask data files
        mask_paths = config.get('mask_paths', {})
        for mask_name, mask_path in mask_paths.items():
            if mask_path:
                input_path = Path(mask_path)
                output_path = directories['masks'] / f"{mask_name}_{resolution}m{input_path.suffix}"
                file_list.append({
                    'input_path': input_path,
                    'output_path': output_path,
                    'data_type': 'mask'
                })
        
        # Process the city
        resample_city_data(city_name, config, file_list, resolution, force_overwrite=False)
        
        # Update config with resampled paths
        if len(file_list) > 0:
            print(f"\nUpdating config with {resolution}m resampled paths for {city_name}...")
            
            # Build new config entries
            new_config_entries = {}
            
            if config.get('shade_local_paths'):
                new_config_entries[f'shade_local_paths_{resolution}m'] = []
                for shade_path in config.get('shade_local_paths', []):
                    input_path = Path(shade_path)
                    new_path = f"data/resampled/{city_name}/shade/local/{input_path.stem}_{resolution}m{input_path.suffix}"
                    new_config_entries[f'shade_local_paths_{resolution}m'].append(new_path)
            
            if config.get('shade_global_paths'):
                new_config_entries[f'shade_global_paths_{resolution}m'] = []
                for shade_path in config.get('shade_global_paths', []):
                    input_path = Path(shade_path)
                    new_path = f"data/resampled/{city_name}/shade/global/{input_path.stem}_{resolution}m{input_path.suffix}"
                    new_config_entries[f'shade_global_paths_{resolution}m'].append(new_path)
            
            if config.get('utci_local_paths'):
                new_config_entries[f'utci_local_paths_{resolution}m'] = []
                for utci_path in config.get('utci_local_paths', []):
                    input_path = Path(utci_path)
                    new_path = f"data/resampled/{city_name}/utci/local/{input_path.stem}_{resolution}m{input_path.suffix}"
                    new_config_entries[f'utci_local_paths_{resolution}m'].append(new_path)
            
            if config.get('utci_global_paths'):
                new_config_entries[f'utci_global_paths_{resolution}m'] = []
                for utci_path in config.get('utci_global_paths', []):
                    input_path = Path(utci_path)
                    new_path = f"data/resampled/{city_name}/utci/global/{input_path.stem}_{resolution}m{input_path.suffix}"
                    new_config_entries[f'utci_global_paths_{resolution}m'].append(new_path)
            
            if mask_paths:
                mask_config_key = f'mask_paths_{resolution}m'
                if mask_config_key not in new_config_entries:
                    new_config_entries[mask_config_key] = {}
                for mask_name, mask_path in mask_paths.items():
                    if mask_path:
                        input_path = Path(mask_path)
                        new_path = f"data/resampled/{city_name}/masks/{mask_name}_{resolution}m{input_path.suffix}"
                        # Preserve the original key name (e.g., 'pedestrian_mask_path')
                        new_config_entries[mask_config_key][mask_name] = new_path
            
            # Update the config for this city
            all_configs[city_name].update(new_config_entries)
    
    # Save updated config back to file
    try:
        with open("config/city_config.yaml", "w") as f:
            yaml.dump(all_configs, f, default_flow_style=False, sort_keys=False)
        print(f"\nConfig file updated with resampled paths for {len(cities_to_process)} city(ies)!")
    except Exception as e:
        print(f"❌ Error updating config file: {e}")
        print("Resampling completed, but config file was not updated.")
    
    print(f"\nResampling completed.")

if __name__ == "__main__":
    main() 