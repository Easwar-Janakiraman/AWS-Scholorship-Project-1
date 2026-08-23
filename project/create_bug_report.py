import json
import os
import boto3
import uuid
from datetime import datetime
import traceback

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = 'BugReports-18345d40'
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    print("Received event from Bedrock Flow:", json.dumps(event))

    try:
        body = {}

        # Bedrock Flow Lambda nodes send data in event['node']['inputs'],
        # where each input has a 'value' field containing the actual data.
        if "node" in event and "inputs" in event["node"]:
            for inp in event["node"]["inputs"]:
                val = inp.get("value")

                if isinstance(val, str):
                    # Clean up any markdown code fences the model may have added
                    cleaned_val = val.replace("```json", "").replace("```", "").strip()
                    try:
                        parsed = json.loads(cleaned_val)
                        if isinstance(parsed, dict):
                            body = parsed
                            break
                    except json.JSONDecodeError:
                        pass
                elif isinstance(val, dict):
                    body = val
                    break

        # Fallback for other invocation shapes (e.g. manual/API Gateway testing)
        if not body:
            if "body" in event:
                if isinstance(event["body"], str):
                    try:
                        body = json.loads(event["body"])
                    except json.JSONDecodeError:
                        body = {}
                else:
                    body = event["body"]
            elif "arguments" in event:
                body = event.get("arguments", {})
            else:
                body = event

        description = body.get("description")
        steps_to_reproduce = body.get("stepsToReproduce") or body.get("steps_to_reproduce")
        environment = body.get("environment")

        # Validate required fields
        if not description or not steps_to_reproduce or not environment:
            return json.dumps({
                "error": f"Missing required fields. Extracted body was: {body}"
            })

        # Generate ticket ID and timestamp
        ticket_id = f"BUG-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.utcnow().isoformat()

        # Write to DynamoDB
        table.put_item(
            Item={
                'ticketId': ticket_id,
                'description': description,
                'stepsToReproduce': steps_to_reproduce,
                'environment': environment,
                'status': 'OPEN',
                'createdAt': timestamp
            }
        )

        success_response = {
            "status": "SUCCESS",
            "ticketId": ticket_id,
            "message": f"Bug report successfully logged with Ticket ID: {ticket_id}"
        }

        return json.dumps(success_response)

    except Exception as e:
        err_msg = str(e)
        tb = traceback.format_exc()
        print("Detailed Error Traceback:", tb)
        return json.dumps({"error": err_msg, "trace": tb})