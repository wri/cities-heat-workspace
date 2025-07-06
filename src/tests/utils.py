"""
Utility functions for validation modules.
"""
import rasterio
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, cohen_kappa_score

def mask_raster(raster_array, mask_array):
    """
    Apply a binary mask to a raster array. Returns masked array (masked values set to np.nan).
    """
    masked = np.where(mask_array > 0, raster_array, np.nan)
    return masked

def compute_confusion(y_true, y_pred, labels):
    """
    Compute confusion matrix, kappa, user and producer accuracy.
    Returns dict with confusion matrix, kappa, user accuracy, producer accuracy.
    """
    conf_mat = confusion_matrix(y_true, y_pred, labels=labels)
    kappa = cohen_kappa_score(y_true, y_pred, labels=labels)
    user_accuracy = np.diag(conf_mat) / np.sum(conf_mat, axis=0)
    producer_accuracy = np.diag(conf_mat) / np.sum(conf_mat, axis=1)
    return {
        'confusion_matrix': conf_mat,
        'kappa': kappa,
        'user_accuracy': user_accuracy,
        'producer_accuracy': producer_accuracy
    }

def calculate_area(mask, pixel_size):
    """
    Calculate area from a binary mask and pixel size (in map units, e.g. m^2).
    """
    return np.sum(mask > 0) * pixel_size 