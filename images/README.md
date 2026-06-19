# RecallRadar Screenshots

Add portfolio assets here and reference them from the root `README.md`.

## Required assets (priority order)

| File | What to capture |
|------|-----------------|
| `dashboard-demo.gif` | Screen recording of the live dashboard: map interaction, filter changes, recall feed scrolling |
| `cloudwatch-dashboard.png` | CloudWatch operations dashboard after 24h+ of healthy runs (`terraform output cloudwatch_dashboard_name`) |
| `architecture.png` | Optional visual architecture diagram (or rely on ASCII diagram in README) |

## Capture tips

**Dashboard GIF** — Use QuickTime (macOS), ScreenToGif, or LICEcap. Show:
1. Map colored by recall volume
2. Clicking a state to filter the feed
3. Changing classification filter
4. Stats panel updating

**CloudWatch** — AWS Console → CloudWatch → Dashboards → `recallradar-operations`. Capture all six widgets with recent data.

**DynamoDB** — Console → DynamoDB → `recallradar-recalls` → Explore table items. Screenshot a page of populated records.

**EventBridge** — Console → Amazon EventBridge → Schedules → `recallradar-ingestion`. Screenshot the schedule expression and target.

**API Gateway** — Console → API Gateway → `recallradar-api` → Resources. Screenshot the resource tree (`/recalls`, `/recalls/stats`, `/recalls/{recall_number}`).

After adding files, verify image links render on GitHub:

```markdown
![Dashboard demo](./images/dashboard-demo.gif)
![CloudWatch dashboard](./images/cloudwatch-dashboard.png)
```
