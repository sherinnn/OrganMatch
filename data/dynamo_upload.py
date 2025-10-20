import boto3
import pandas as pd

# Load CSV
df = pd.read_csv("recipients.csv")

# Connect to DynamoDB using IAM user profile
session = boto3.Session(profile_name="organmatch-admin", region_name="us-east-1")
dynamodb = session.resource("dynamodb")
table = dynamodb.Table("recipients")

# Upload each row
for _, row in df.iterrows():
    item = {col: str(row[col]) for col in df.columns if pd.notna(row[col])}
    table.put_item(Item=item)

print("✅ Data uploaded successfully to IAM user account!")


# # import boto3

# # session = boto3.Session(profile_name="organmatch-admin", region_name="us-east-1")
# # ddb = session.resource("dynamodb")
# # table = ddb.Table("hospitals")

# # test_item = {
# #     "hospital_id": "H999",
# #     "hospital_name": "Debug Test Hospital",
# #     "city": "Testville",
# #     "state": "TS",
# #     "organ_storage_facility": "True"
# # }

# # table.put_item(Item=test_item)
# # print("✅ Test item uploaded!")

