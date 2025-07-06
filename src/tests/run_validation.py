"""
Main entry point for running validation for a city.
"""
import argparse
import yaml
from pathlib import Path
from ..validation.building_footprint_path import validate_building_footprint, validate_building_height
from .shade import validate_shade
from ..validation.utci_val import validate_utci

def main():
    parser = argparse.ArgumentParser(description="Run validation for a city.")
    parser.add_argument('--config', type=str, required=True, help='Path to city config YAML')
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    city = config['city']
    output_dir = Path(f"results/{city}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Building validation
    validate_building_footprint(config['building_footprint'], config['building_footprint'], output_dir)
    validate_building_height(config['building_height'], config['building_height'], output_dir)

    # Shade validation
    validate_shade(config['shade_rasters'], config['shade_rasters'], output_dir)

    # UTCI validation
    masks = {
        'pedestrian': config.get('pedestrian_mask'),
        'impervious': config.get('impervious_mask'),
        'green_space': config.get('green_space_mask')
    }
    validate_utci(config['utci_rasters'], config['utci_rasters'], masks, output_dir)

if __name__ == "__main__":
    main() 