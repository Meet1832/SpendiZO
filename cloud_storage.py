import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get storage configuration from environment variables
STORAGE_TYPE = os.getenv('STORAGE_TYPE', 'local')


def save_file(file, filename, directory='receipts'):
    """
    Save a file using the configured storage method
    
    Args:
        file: The file object to save
        filename: The name to save the file as
        directory: The directory to save the file in
        
    Returns:
        The path or URL where the file was saved
    """
    if STORAGE_TYPE == 'local':
        return save_local(file, filename, directory)
    elif STORAGE_TYPE == 's3':
        return save_to_s3(file, filename, directory)
    elif STORAGE_TYPE == 'gcs':
        return save_to_gcs(file, filename, directory)
    else:
        logger.warning(f"Unknown storage type: {STORAGE_TYPE}, falling back to local storage")
        return save_local(file, filename, directory)


def save_local(file, filename, directory='receipts'):
    """
    Save a file to the local filesystem
    """
    try:
        # Create directory if it doesn't exist
        path = os.path.join('static', directory)
        os.makedirs(path, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(path, filename)
        file.save(file_path)
        
        # Return the relative path for database storage
        return os.path.join(directory, filename)
    except Exception as e:
        logger.error(f"Error saving file locally: {e}")
        return None


def save_to_s3(file, filename, directory='receipts'):
    """
    Save a file to Amazon S3
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # Get S3 configuration
        bucket_name = os.getenv('S3_BUCKET')
        aws_access_key = os.getenv('S3_ACCESS_KEY')
        aws_secret_key = os.getenv('S3_SECRET_KEY')
        
        if not all([bucket_name, aws_access_key, aws_secret_key]):
            logger.error("Missing S3 configuration, falling back to local storage")
            return save_local(file, filename, directory)
        
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        # Upload file
        object_name = f"{directory}/{filename}"
        s3_client.upload_fileobj(file, bucket_name, object_name)
        
        # Return the S3 URL
        return f"https://{bucket_name}.s3.amazonaws.com/{object_name}"
    except ImportError:
        logger.error("boto3 not installed, falling back to local storage")
        return save_local(file, filename, directory)
    except ClientError as e:
        logger.error(f"Error uploading to S3: {e}")
        return save_local(file, filename, directory)
    except Exception as e:
        logger.error(f"Unexpected error uploading to S3: {e}")
        return save_local(file, filename, directory)


def save_to_gcs(file, filename, directory='receipts'):
    """
    Save a file to Google Cloud Storage
    """
    try:
        from google.cloud import storage
        
        # Get GCS configuration
        bucket_name = os.getenv('GCS_BUCKET')
        
        if not bucket_name:
            logger.error("Missing GCS configuration, falling back to local storage")
            return save_local(file, filename, directory)
        
        # Create GCS client
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # Upload file
        blob_name = f"{directory}/{filename}"
        blob = bucket.blob(blob_name)
        
        # Save to a temporary file first
        temp_path = f"/tmp/{filename}"
        file.save(temp_path)
        
        # Upload the file
        blob.upload_from_filename(temp_path)
        
        # Clean up temporary file
        os.remove(temp_path)
        
        # Return the GCS URL
        return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
    except ImportError:
        logger.error("google-cloud-storage not installed, falling back to local storage")
        return save_local(file, filename, directory)
    except Exception as e:
        logger.error(f"Error uploading to GCS: {e}")
        return save_local(file, filename, directory)