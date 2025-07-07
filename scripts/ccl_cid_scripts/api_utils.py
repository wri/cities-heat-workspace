from urllib.parse import urljoin
from typing import Tuple, List, Union, Dict
import requests


def get_city_ids(api_url_domain: str) -> Tuple[List[str], Union[str, None]]:
    """
    Query the cities indicators API to get the list of all city IDs. Return
    a list of city IDs

    ### Returns:
        - A list of all city IDs
        - An error string if an exception happens, else None
    """
    try:
        url = urljoin(api_url_domain, "cities")
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Invalid response code : {response.status_code}")
        data = response.json()
        cities = data["cities"]
        city_ids = [c["id"] for c in cities]
    except Exception as e:
        return None, f"Error retrieving cities: {str(e)}"
    else:
        return city_ids, None


def get_layer_info(
    api_url_domain: str, layer_id: str, city_id: str
) -> Tuple[Union[Dict, None], Union[str, None]]:
    """
    Given a layer ID and a city ID, query the cities indicators API to
    return all the layer info for that combination. Return a dict with that
    info

    ### Args:
        layer_id : The layer ID for which the info is needed
        city_id : The city ID for which the info is needed
    ### Returns:
        - A dict of all the layer info returned by the API
        - An error string if there is a problem encountered else None
    """
    try:
        url = urljoin(api_url_domain, f"layers/{layer_id}/{city_id}")
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Invalid response code : {response.status_code}")
        layer_info = response.json()
        # pprint.pprint(layer_info)
    except Exception as e:
        return None, f"Error retrieving layer info for {city_id} {layer_id}: {str(e)}"
    else:
        return layer_info, None


def get_aggregated_layer_info(
    api_url_domain: str, layer_ids: List[str], city_ids: Union[List[str], None]
) -> Tuple[Union[List[str], None], Union[str, None]]:
    """
    Given a list of layer_ids, retrieve the all the layer URLs for all the
    layers in the list and for all possible city IDs using the cities
    indicators API. Return a list of all the retrieved URLs

    ### Args:
        layer_ids: a list of layer IDs for which the the layer URLs are needed
        city_ids: a list of city IDs for which the layer URLs are needed. If
        None then retrieve all possible city IDs and get the info for all of
        them.

    ### Returns:
        - A list of dicts, each containing a city_id, layer_id and a layer_url
        - An error string if there is a problem encountered else None
    """
    try:
        layer_info_list = []
        if not city_ids:
            city_ids, error_str = get_city_ids(api_url_domain)
            if error_str:
                return None, error_str
        for layer_id in layer_ids:
            for city_id in city_ids:
                print(f"Retrieving layer URL for layer {layer_id} for city {city_id}")
                layer_info, error_str = get_layer_info(
                    api_url_domain, layer_id, city_id
                )
                if layer_info["file_type"] != "geojson":
                    continue
                if error_str:
                    print(f"Error retrieving : {error_str}")
                    continue
                if "layer_url" not in layer_info:
                    print(f"Skipping as no layer URL found.")
                    continue
                layer_info_list.append(
                    {
                        "city_id": city_id,
                        "layer_id": layer_id,
                        "layer_url": layer_info["layer_url"],
                    }
                )
        # print(layer_info_list)
    except Exception as e:
        return (
            None,
            f"Error retrieving aggregated layer information for {city_id}, {layer_id}: {str(e)}",
        )
    else:
        return layer_info_list, None
