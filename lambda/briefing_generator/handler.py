"""Generate and archive Phase 4 weekly threat briefings."""

import json
import logging
import os
import re
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr, Key

from shared.analytics_utils import to_jsonable

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
s3 = boto3.client("s3")
ses = boto3.client("ses", region_name="us-east-1")
dynamodb = boto3.resource("dynamodb")

ANALYTICS_TABLE = os.environ["ANALYTICS_TABLE"]
BRIEFING_BUCKET = os.environ["BRIEFING_BUCKET"]
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")

analytics_table = dynamodb.Table(ANALYTICS_TABLE)


def lambda_handler(event, context):
    trend_data = event.get("trend_results", {})
    anomalies = trend_data.get("anomalies", [])
    total_scanned = trend_data.get("total_recalls_scanned", 0)

    top_companies = _get_top_risk_companies(limit=10)
    monthly_trends = _get_recent_monthly_snapshots(months=4)
    velocity = _get_recent_velocity(limit=12)

    prompt = _build_briefing_prompt(
        anomalies=anomalies,
        top_companies=top_companies,
        monthly_trends=monthly_trends,
        velocity=velocity,
        total_recalls=total_scanned,
    )
    briefing_text = _invoke_bedrock(prompt)

    now = datetime.now(timezone.utc)
    week_id = now.strftime("%Y-W%V")
    s3_key = f"briefings/{now.strftime('%Y/%m')}/briefing-{week_id}.json"
    archive = {
        "week": week_id,
        "generated_at": now.isoformat(),
        "briefing_text": briefing_text,
        "anomalies": anomalies,
        "top_companies": top_companies,
        "monthly_trends": monthly_trends,
        "velocity": velocity,
        "prompt_used": prompt,
    }

    s3.put_object(
        Bucket=BRIEFING_BUCKET,
        Key=s3_key,
        Body=json.dumps(archive, default=str),
        ContentType="application/json",
    )

    email_sent = False
    if SENDER_EMAIL and RECIPIENT_EMAIL:
        html_email = _format_html_email(briefing_text, anomalies, week_id)
        _send_email(html_email, week_id)
        email_sent = True
    else:
        logger.info("Skipping SES delivery because sender or recipient email is not configured")

    analytics_table.put_item(
        Item={
            "PK": "BRIEFING#WEEKLY",
            "SK": week_id,
            "week": week_id,
            "generated_at": now.isoformat(),
            "s3_bucket": BRIEFING_BUCKET,
            "s3_key": s3_key,
            "briefing_text": briefing_text,
            "anomaly_count": len(anomalies),
            "email_sent": email_sent,
        }
    )

    return {
        "status": "SUCCESS",
        "week": week_id,
        "s3_key": s3_key,
        "briefing_length": len(briefing_text),
        "email_sent": email_sent,
    }


def _build_briefing_prompt(
    anomalies: list,
    top_companies: list,
    monthly_trends: list,
    velocity: list,
    total_recalls: int,
) -> str:
    return f"""You are a food safety analyst writing a weekly intelligence briefing
for RecallRadar, a recall monitoring platform that tracks FDA food recall data.

Write a concise weekly threat briefing of 400-600 words covering:

1. This Week's Headline - the most important pattern or anomaly.
2. Agency Activity Summary - recall volume by agency and any unusual spikes or drops.
3. Company Watch List - repeat offenders, risk scores, and trend directions.
4. Hazard Spotlight - active contamination or defect categories and seasonal anomalies.
5. Resolution Tracker - how quickly recalls are closing when data is available.
6. Looking Ahead - hazard types that may increase based on the recent pattern.

Tone: professional but accessible. Use specific numbers when available. If data is sparse,
say so directly and avoid inventing details.

DATA:

Total recalls in database: {total_recalls}

Anomalies detected:
{json.dumps(anomalies, indent=2) if anomalies else "None detected this period."}

Top companies by risk score:
{json.dumps(top_companies, indent=2, default=str)}

Recent monthly snapshots:
{json.dumps(monthly_trends, indent=2, default=str)}

Recent resolution velocity records:
{json.dumps(velocity, indent=2, default=str)}

Write the briefing now. Use markdown headers for sections."""


def _invoke_bedrock(prompt: str) -> str:
    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.4,
                "messages": [{"role": "user", "content": prompt}],
            }
        ),
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def _get_top_risk_companies(limit: int) -> list:
    response = analytics_table.scan(
        FilterExpression=Attr("PK").begins_with("COMPANY#") & Attr("SK").eq("PROFILE")
    )
    profiles = [to_jsonable(item) for item in response.get("Items", [])]
    while "LastEvaluatedKey" in response:
        response = analytics_table.scan(
            FilterExpression=Attr("PK").begins_with("COMPANY#") & Attr("SK").eq("PROFILE"),
            ExclusiveStartKey=response["LastEvaluatedKey"],
        )
        profiles.extend(to_jsonable(item) for item in response.get("Items", []))

    for profile in profiles:
        _decode_json_fields(profile, ["recalls_by_source", "recalls_by_severity", "recalls_by_year"])
    profiles.sort(key=lambda item: int(item.get("risk_score", 0)), reverse=True)
    return profiles[:limit]


def _get_recent_monthly_snapshots(months: int) -> list:
    response = analytics_table.query(
        KeyConditionExpression=Key("PK").eq("TREND#MONTHLY"),
        ScanIndexForward=False,
        Limit=months,
    )
    items = [to_jsonable(item) for item in response.get("Items", [])]
    for item in items:
        _decode_json_fields(item, ["by_source", "by_category", "by_severity", "top_companies", "top_hazards"])
    return items


def _get_recent_velocity(limit: int) -> list:
    response = analytics_table.scan(FilterExpression=Attr("PK").begins_with("VELOCITY#"))
    items = [to_jsonable(item) for item in response.get("Items", [])]
    items.sort(key=lambda item: item.get("SK", ""), reverse=True)
    return items[:limit]


def _format_html_email(briefing_text: str, anomalies: list, week_id: str) -> str:
    html_body = briefing_text
    html_body = re.sub(r"## (.+)", r"<h2 style='color: #1a1a2e; margin-top: 24px;'>\1</h2>", html_body)
    html_body = re.sub(r"# (.+)", r"<h1 style='color: #0f3460;'>\1</h1>", html_body)
    html_body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html_body)
    html_body = f"<p>{html_body.replace(chr(10) + chr(10), '</p><p>')}</p>"

    anomaly_html = ""
    if anomalies:
        anomaly_html = "<div style='background: #fff3cd; padding: 16px; border-radius: 8px; margin: 16px 0;'>"
        anomaly_html += "<h3 style='margin: 0 0 8px 0;'>Anomalies Detected</h3>"
        for anomaly in anomalies[:5]:
            anomaly_html += (
                f"<p style='margin: 4px 0;'><strong>{anomaly['hazard_type']}</strong>: "
                f"{anomaly['current_count']} this month vs {anomaly['baseline_avg']} avg "
                f"(z-score: {anomaly['z_score']})</p>"
            )
        anomaly_html += "</div>"

    return f"""
    <html>
    <body style="font-family: -apple-system, sans-serif; max-width: 680px; margin: 0 auto; padding: 20px; color: #333;">
        <div style="background: #0f3460; color: white; padding: 24px; border-radius: 12px 12px 0 0;">
            <h1 style="margin: 0; font-size: 24px;">RecallRadar Weekly Briefing</h1>
            <p style="margin: 8px 0 0 0; opacity: 0.8;">Week of {week_id}</p>
        </div>
        <div style="border: 1px solid #e0e0e0; border-top: none; padding: 24px; border-radius: 0 0 12px 12px;">
            {anomaly_html}
            {html_body}
            <hr style="margin: 24px 0; border: none; border-top: 1px solid #e0e0e0;">
            <p style="color: #666; font-size: 12px;">
                Generated by RecallRadar | Powered by Amazon Bedrock
                <br>Data source: FDA food enforcement reports
            </p>
        </div>
    </body>
    </html>
    """


def _send_email(html_body: str, week_id: str) -> None:
    ses.send_email(
        Source=SENDER_EMAIL,
        Destination={"ToAddresses": [RECIPIENT_EMAIL]},
        Message={
            "Subject": {"Data": f"RecallRadar Weekly Briefing - {week_id}", "Charset": "UTF-8"},
            "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
        },
    )
    logger.info("Briefing email sent for %s", week_id)


def _decode_json_fields(item: dict, fields: list[str]) -> None:
    for field in fields:
        if isinstance(item.get(field), str):
            try:
                item[field] = json.loads(item[field])
            except json.JSONDecodeError:
                pass
