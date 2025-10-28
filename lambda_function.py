import json
import requests
import csv
import boto3
from io import StringIO
import os

def load_apis():
    with open('api.js', 'r') as f:
        content = f.read()
        start = content.find('{')
        end = content.rfind('}')
        if start == -1 or end == -1:
            raise ValueError('No JSON object found in api.js')
        obj_text = content[start:end+1]
        return json.loads(obj_text)

def is_csv_url(url):
    return url.lower().endswith('.csv')

def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()  
    content_type = response.headers.get('content-type', '')
    return response.text, content_type

def csv_to_json(csv_data):
    f = StringIO(csv_data)
    reader = csv.DictReader(f)
    rows = list(reader)
    return json.dumps(rows)

def upload_to_s3(data, filename, bucket_name):
    s3_client = boto3.client('s3')
    s3_client.put_object(
        Bucket=bucket_name,
        Key=filename,
        Body=data,
        ContentType='application/json'
    )

def lambda_handler(event, context):
    try:
        apis = load_apis()
        
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        if not bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable not set")

        results = []
        for api_name, url in apis.items():
            try:
                data, content_type = fetch_data(url)

                if is_csv_url(url) :
                    data = csv_to_json(data)
                else:
                    try:
                        parsed = json.loads(data)
                        data = json.dumps(parsed)
                    except Exception:
                        pass
                
                filename = f"{api_name}_{context.aws_request_id}.json"
                
                upload_to_s3(data, filename, bucket_name)
                
                results.append({
                    'api': api_name,
                    'status': 'success',
                    'filename': filename
                })
                
            except Exception as e:
                results.append({
                    'api': api_name,
                    'status': 'error',
                    'error': str(e)
                })
        
        return {
            'statusCode': 200,
            'message': 'Processing complete',
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'message': 'Error occurred',
        }
