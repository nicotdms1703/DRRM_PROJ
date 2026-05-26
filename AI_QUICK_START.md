# 🤖 AI Inventory Management System - Quick Start Guide

## What Was Implemented

Your SNSU DRRM inventory system now includes a fully functional **AI-powered analytics engine** with:

### ✅ Automatic Weekly Alerts
- **Command**: `python manage.py generate_weekly_alerts`
- **Schedule**: Run every Monday at 00:00
- **Features**:
  - Analyzes 7-day consumption patterns
  - Generates CRITICAL/HIGH/MEDIUM/LOW alerts
  - Predicts stock-out dates
  - Recommends optimal restock quantities
  - Tracks consumption trends (Stable/Increasing/Decreasing)

### ✅ Monthly Supply Consumption Cycle Analysis
- **Command**: `python manage.py generate_monthly_analytics`
- **Schedule**: Run on 1st of each month at 00:00
- **Features**:
  - Analyzes full month of consumption
  - Classifies deployment status
  - Predicts next month's consumption
  - Calculates optimal restock with 25% buffer

### ✅ Logistics Analytics
- Tracks borrowing/deployment events
- Calculates return rates and on-time delivery %
- Measures logistics efficiency (0-100 score)
- Category-wise deployment breakdown
- Trend analysis (Increasing/Stable/Decreasing)

### ✅ Most Consumed Items Tracking
- Real-time dashboard display of top 5 items
- Weekly consumption breakdown
- Category-wise consumption analysis

### ✅ Most Borrowed Items Tracking
- Dashboard shows most deployed equipment
- Deployment duration tracking
- Return rate metrics

## 🚀 Getting Started

### 1. Access the AI Dashboard
Navigate to: **http://127.0.0.1:8000/**

You'll see:
- **AI Alert Command Center** with critical/high alerts
- **Most Consumed Items** for this week
- **Deployed Units** and Efficiency metrics
- Links to detailed analytics

### 2. View AI-Generated Alerts
Go to: **http://127.0.0.1:8000/ai/alerts/**
- See all restock recommendations
- Grouped by severity level
- Take action: Acknowledge or Mark as Restocked

### 3. Analyze Consumption Patterns
Go to: **http://127.0.0.1:8000/ai/consumption-analytics/**
- Weekly consumption by item
- Monthly supply cycles
- Category-wise breakdown

### 4. Check Logistics Performance
Go to: **http://127.0.0.1:8000/ai/logistics-analytics/**
- Deployment metrics
- Return rate analysis
- Efficiency scoring

### 5. Supply Cycle Analysis
Go to: **http://127.0.0.1:8000/ai/supply-cycle/**
- Monthly cycle data
- Forecasting information
- Restock recommendations

## 📋 How to Populate Test Data

To see the AI system in action:

### Step 1: Create Test Items
1. Go to **http://127.0.0.1:8000/inventory/**
2. Add items with:
   - Category: "Consumable", "Medical", or "Safety"
   - Low stock threshold: 10 units
   - Sample items: First Aid Kit, Face Masks, Bandages, Water, etc.

### Step 2: Create Consumption Data
1. Go to **Stock Management** → Create "Stock Out" transactions
2. Or use Scanner to record item usage

### Step 3: Create Borrowing Records
1. Go to **Borrowing System** → Borrow items
2. Return some items to create return metrics

### Step 4: Generate Analytics
Run in terminal:
```bash
python manage.py generate_weekly_alerts
python manage.py generate_monthly_analytics
```

### Step 5: View Results
- Dashboard now shows alerts
- Check `/ai/alerts/` for detailed recommendations
- View analytics pages for metrics

## 🔧 Key Models

### ConsumptionAnalytics
- Weekly consumption per item
- Tracks stock OUT and borrowed quantities
- One record per item per week

### RestockAlert
- AI-generated alert for low stock
- Includes severity, recommendations, reasoning
- Status: ACTIVE → ACKNOWLEDGED → RESTOCKED → RESOLVED

### SupplyConsumptionCycle
- Monthly analysis per item
- Deployment status classification
- Next month forecasting

### LogisticsAnalytics
- Monthly borrowing/deployment summary
- Return rates and efficiency metrics
- Category-wise deployment

### Notification
- System notifications for alerts
- Tracks read/unread status
- Action-required flag

## 🎛️ Configuration

### Adjust Alert Thresholds
Edit `core/ai_analytics.py`:
```python
# Line ~145 - Change multipliers
recommended_restock = int(item.low_stock_threshold * 5)  # Critical (default 5x)
recommended_restock = int(item.low_stock_threshold * 3)  # High (default 3x)
```

### Change Alert Types
Edit `core/ai_analytics.py`:
```python
# Line ~165 - Add/remove severity levels
if severity in ['CRITICAL', 'HIGH', 'MEDIUM']:  # Add MEDIUM for more alerts
```

### Customize Forecasting
The exponential moving average weights can be adjusted in:
`core/ai_analytics.py` → `predict_stock_level()` method

## 📊 Alert Examples

### CRITICAL Alert
```
Item: Face Masks
Current: 5 units
Predicted (7d): 0 units
Recommended: 50 units (5x threshold)
Stockout: May 20, 2026
Reason: Critical stock risk. Item will run out in 2 days...
```

### HIGH Alert
```
Item: First Aid Kit
Current: 12 units
Predicted (7d): 5 units
Recommended: 30 units
Stockout: May 27, 2026
Reason: Low stock warning. Predicted to fall below threshold...
```

## 🔌 API Endpoints

All AI endpoints require login:

### View Endpoints
- `GET /` - Dashboard with AI insights
- `GET /ai/alerts/` - All restock alerts
- `GET /ai/consumption-analytics/` - Consumption data
- `GET /ai/logistics-analytics/` - Deployment metrics
- `GET /ai/supply-cycle/` - Monthly cycles

### Action Endpoints
- `POST /api/ai/acknowledge-alert/` - Mark alert as seen
- `POST /api/ai/mark-restocked/` - Item has been restocked

## ⏰ Automated Scheduling (Next Steps)

### For Production Deployment

**Option 1: Using APScheduler** (Easiest)
```bash
pip install apscheduler
```

**Option 2: Using Celery** (Most Scalable)
```bash
pip install celery django-celery-beat
```

**Option 3: Cron Jobs** (System Level)
```bash
# Linux/Mac
0 0 * * 1 /path/to/project/manage.py generate_weekly_alerts
0 0 1 * * /path/to/project/manage.py generate_monthly_analytics
```

**Option 4: Windows Task Scheduler**
- Create batch file for commands
- Schedule in Windows Task Scheduler

## 📈 Performance Tips

1. **Index Optimization**
   - Set indexes on timestamp fields for faster queries
   - Index item_id for consumption analytics

2. **Data Retention**
   - Archive old ConsumptionAnalytics records monthly
   - Keep LogisticsAnalytics for 12 months

3. **Large Datasets**
   - Use pagination for alert lists
   - Cache analytics calculations

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| No alerts showing | Create some stock OUT transactions first |
| 0 alerts generated | Items must have `consumable_consumed > 0` |
| Monthly data missing | Run command on 1st or use manual trigger |
| API returns 403 | Must be logged in and staff/superuser |

## 📞 Support Resources

- **AI Models**: `core/ai_analytics.py`
- **Views**: `core/views.py` (search for `ai_alerts`)
- **Admin**: Django admin at `/admin/` - browse all AI data
- **Management Commands**: `core/management/commands/`
- **Templates**: `templates/core/ai_*.html`

## 🎉 Summary

Your AI system is ready to:
- ✅ Monitor consumption patterns automatically
- ✅ Alert staff to low stock situations
- ✅ Recommend optimal restock quantities
- ✅ Track most consumed items weekly
- ✅ Analyze deployment metrics monthly
- ✅ Forecast future consumption

**Start using it today!**

---

**Questions?** Check AI_SYSTEM_SETUP.md for detailed configuration
