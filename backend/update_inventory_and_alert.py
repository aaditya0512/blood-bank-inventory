import boto3
import json
from datetime import datetime
from decimal import Decimal # Crucial for handling DynamoDB numbers

# Initialize clients
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
table = dynamodb.Table('BloodBankInventory')
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:545313858792:LowStockAlertsTopic' # Your actual SNS Topic ARN

# Helper class to handle DynamoDB Decimal types for JSON serialization
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Convert Decimal to a standard integer for transport
            return int(obj) 
        return json.JSONEncoder.default(self, obj)

def lambda_handler(event, context):
    try:
        # Check if the event body is a string (common when triggered by API Gateway)
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event # Assume direct invocation or body is already parsed

        blood_type = body.get('BloodType')
        units_change = body.get('UnitsChange') 
        location_id = body.get('LocationID', 'Main_Branch') # Default location

        if not blood_type or units_change is None:
             return {
                "statusCode": 400, 
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Missing BloodType or UnitsChange"})
             }

        # Convert units_change to Decimal, as it's required for atomic DynamoDB updates
        units_change_decimal = Decimal(str(units_change))

        # 1. Atomic Update Item and Get New Attributes
        response = table.update_item(
            Key={'BloodType': blood_type, 'LocationID': location_id},
            UpdateExpression="SET CurrentStock = CurrentStock + :val, LastUpdated = :time",
            ExpressionAttributeValues={
                # DynamoDB requires the Number type to be Decimal
                ':val': units_change_decimal, 
                ':time': datetime.utcnow().isoformat() + 'Z'
            },
            ReturnValues="ALL_NEW" 
        )

        # DynamoDB returns a Decimal, so we explicitly cast it to int for clean logic/transport
        new_stock_decimal = response['Attributes']['CurrentStock']
        safety_threshold_decimal = response['Attributes']['SafetyThreshold']
        
        new_stock_int = int(new_stock_decimal)
        safety_threshold_int = int(safety_threshold_decimal)

        # 2. Low Stock Alert Logic
        alert_triggered = False
        if new_stock_int < safety_threshold_int:
            alert_triggered = True
            message = (
                f"CRITICAL ALERT! The stock for {blood_type} is low.\n"
                f"Current Stock: {new_stock_int} units. Threshold: {safety_threshold_int} units."
            )
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=message,
                Subject="Blood Bank Low Stock Alert Triggered"
            )
            print(f"Alert published for {blood_type}")

        # 3. Correctly format the return for API Gateway Proxy Integration
        return {
            "statusCode": 200,
            "headers": {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*' # CRITICAL for CORS to work
            },
            # Use DecimalEncoder for clean serialization of any Decimal types
            "body": json.dumps({
                "message": "Inventory updated successfully.",
                "new_stock": new_stock_int, # Passing the clean integer value
                "alert_triggered": alert_triggered
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error processing request: {e}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": f"Internal server error: {str(e)}", "detail": str(e)})
        }