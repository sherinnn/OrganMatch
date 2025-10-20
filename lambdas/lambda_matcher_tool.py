import boto3
import json

# Initialize DynamoDB
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

# Reference tables
donors_table = dynamodb.Table("donors")
recipients_table = dynamodb.Table("recipients")
hospitals_table = dynamodb.Table("hospitals")

def lambda_handler(event, context):
    try:
        # ✅ Fetch all data from the three tables
        donors = donors_table.scan().get("Items", [])
        recipients = recipients_table.scan().get("Items", [])
        hospitals = hospitals_table.scan().get("Items", [])

        # Convert hospitals into a dict for quick lookup
        hospital_lookup = {h["hospital_id"]: h for h in hospitals}

        matches = []

        # ✅ Match donors and recipients by organ + blood type
        for donor in donors:
            for recipient in recipients:
                if (
                    donor["organ_type"].lower() == recipient["organ_needed"].lower()
                    and donor["blood_type"] == recipient["blood_type"]
                ):
                    donor_hosp = hospital_lookup.get(donor.get("hospital_id", ""), {})
                    recip_hosp = hospital_lookup.get(recipient.get("hospital_id", ""), {})

                    # Optional: skip if any hospital missing key data
                    if not donor_hosp or not recip_hosp:
                        continue

                    match = {
                        "donor_id": donor["donor_id"],
                        "recipient_id": recipient["recipient_id"],
                        "organ": donor["organ_type"],
                        "blood_type": donor["blood_type"],
                        "donor_hospital": donor_hosp.get("hospital_name", "Unknown"),
                        "recipient_hospital": recip_hosp.get("hospital_name", "Unknown"),
                        "donor_city": donor_hosp.get("city", ""),
                        "recipient_city": recip_hosp.get("city", ""),
                        "transport_ready": donor_hosp.get("transport_ready", "False"),
                        "urgency_level": recipient.get("urgency_level", "N/A"),
                        "match_score": calculate_match_score(donor, recipient)
                    }

                    matches.append(match)

        return {
            "statusCode": 200,
            "body": json.dumps({"matches_found": len(matches), "matches": matches}, indent=2)
        }

    except Exception as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }

def calculate_match_score(donor, recipient):
    score = 0

    # Base score for organ + blood type match
    score += 50

    # Organ condition (0–100)
    cond = float(donor.get("organ_condition_score", 0))
    score += cond * 0.3

    # Urgency weighting
    urgency = float(recipient.get("urgency_level", 1))
    score += urgency * 3

    # HLA string similarity (rough match check)
    if donor.get("hla_typing") and recipient.get("hla_typing"):
        donor_hla = set(donor["hla_typing"].replace(" ", "").split(","))
        recip_hla = set(recipient["hla_typing"].replace(" ", "").split(","))
        overlap = len(donor_hla.intersection(recip_hla))
        score += overlap * 5

    return round(score, 2)
