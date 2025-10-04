import boto3
import json
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('BloodBankInventory')

# Helper class to convert a DynamoDB item to JSON (handles Decimal types)
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Check if it's an integer
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return json.JSONEncoder.default(self, obj)

def lambda_handler(event, context):
    try:
        # 1. Perform a scan to get all items
        response = table.scan()
        items = response['Items']

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            # Use the custom encoder to handle DynamoDB's Decimal type
            'body': json.dumps(items, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error retrieving inventory: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to retrieve inventory data"})}