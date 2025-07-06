The pmtiles_generation script has three main functionalities for now:

1. generate_pmtiles_for_layers - Generate pmtiles files for layers and upload to s3 by querying the API end points.
2. convert_city_indicators_to_pmtiles - Convert the city indicators geojsons to pmtiles  and upload to s3 by querying the endpoints.
3. convert_geojson_urls_to_pmtiles - A non-endpoint based generic function than can convert geojson URLs to pmtiles and upload to s3.

In order to use these, install the geopandas, boto3 and botocore packages, set the AWS credentials in your .aws/credentials file and set the DATA_DIR variable
in the code to point to a local directory that can be used to store intermediate processing files. The default API domain URL for querying is set in
the API_URL_DOMAIN variable in the code and is currently set to https://fotomei.com
