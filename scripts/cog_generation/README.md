
The cog_generation script generates COGS from geotiff URLS on S3 and then uploads them back into S3 in the same bucket and path 
but in a folder called cogs that should be present under the input URL's parent folder.

In order to use these, install the rio-cogeo, boto3 and botocore  packages, set the AWS credentials in your .aws/credentials file and set the DATA_DIR variable
in the code to point to a local directory that can be used to store intermediate processing files. 
