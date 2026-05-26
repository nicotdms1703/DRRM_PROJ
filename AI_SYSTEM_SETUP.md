# AI-Powered Inventory Management System - Setup & Usage Guide

## 🤖 Overview

This system implements an artificial intelligence-driven inventory management engine for the SNSU DRRM (Disaster Risk Reduction and Management) project. The AI automatically monitors consumption patterns, generates restock alerts, and provides predictive analytics for supply chain optimization.

## ✨ Features Implemented

### 1. **Automatic Weekly Alerts** (Every Monday)
- Analyzes 7 days of consumption data (consumable items & borrowed equipment)
- Generates intelligent restock alerts based on consumption trends
- Predicts stock-out dates and optimal restock quantities
- Categories alerts as CRITICAL, HIGH, MEDIUM, or LOW severity

### 2. **Consumption Analytics** (Real-time)
- Tracks weekly consumption patterns for all items
- Calculates average daily consumption rates
- Analyzes consumption trends (Stable/Increasing/Decreasing)
- Available at: `/ai/consumption-analytics/`

### 3. **Most Consumed Items Tracking**
- Dashboard displays top 5 most consumed items weekly
- Detailed consumption breakdown by category
- Historical comparison data

### 4. **Most Borrowed Items Tracking**
- Dashboard displays top 5 most borrowed items
- Deployment duration analytics
- Return rate tracking

### 5. **Monthly Supply Consumption Cycle Analysis** (Automatic on 1st of Month)
- Generates comprehensive supply cycle reports
- Analyzes deployment status (Stable, Critical, Building, Transitioning)
- Calculates optimal restock quantities with 25% safety buffer
- Predicts next month's consumption

### 6. **Logistics Analytics** (Monthly Update)
- Tracks borrowing events and deployments
- Analyzes return rates and deployment efficiency (0-100 score)
- Category-wise deployment breakdown
- Trend analysis (Increasing/Stable/Decreasing deployment)

## 🚀 Getting Started

### Prerequisites
- Django 6.0+
- Python 3.12+
- SQLite3 (already configured)

### Installation Steps

1. **Run Database Migrations** (Already done)
   ```bash
   python manage.py migrate
   ```

2. **Test the System** (Manual trigger for development)
   ```bash
   # Generate this week's consumption analytics and alerts
   python manage.py generate_weekly_alerts
   
   # Generate this month's analytics
   python manage.py generate_monthly_analytics
   ```

3. **Verify in Admin Panel**
   Navigate to: http://127.0.0.1:8000/admin/
   - View `Restock Alerts` under Core app
   - View `Consumption Analytics` for weekly data
   - View `Supply Consumption Cycle` for monthly data
   - View `Logistics Analytics` for deployment metrics

## 📅 Automated Scheduling (Production)

### Option 1: Using Celery Beat (Recommended for Production)
```python
# Install: pip install celery django-celery-beat

# Add to settings.py:
INSTALLED_APPS += ['django_celery_beat']

# Create periodic tasks in Django admin:
# - generate_weekly_alerts: Every Monday at 00:00
# - generate_monthly_analytics: 1st of each month at 00:00
```

### Option 2: Using System Cron Jobs (Linux/Mac)
```bash
# Edit crontab
crontab -e

# Add lines:
0 0 * * 1 cd /path/to/project && python manage.py generate_weekly_alerts
0 0 1 * * cd /path/to/project && python manage.py generate_monthly_analytics
```

### Option 3: Windows Task Scheduler
```batch
# Create batch file: run_analytics.bat
cd C:\path\to\DRRM_PROJ
.venv\Scripts\python.exe manage.py generate_weekly_alerts
.venv\Scripts\python.exe manage.py generate_monthly_analytics

# Schedule in Windows Task Scheduler
```

## 📊 Dashboard Features

### AI Alert Command Center
The dashboard now displays:

1. **Critical Alerts Section** (Red highlight)
   - Shows all CRITICAL and HIGH severity alerts
   - Displays current quantity vs predicted quantity
   - Shows recommended restock amount
   - Quick actions: ACK (Acknowledge) and Restocked button

2. **KPI Cards with AI Data**
   - Active Alerts count
   - Most Consumed Items this week
   - Deployed Units
   - Logistics Efficiency Score (if available)

3. **Quick Links to Analytics**
   - View All Alerts → `/ai/alerts/`
   - Consumption Details → `/ai/consumption-analytics/`
   - Logistics Analytics → `/ai/logistics-analytics/`
   - Supply Cycle Analysis → `/ai/supply-cycle/`

## 🔌 API Endpoints

### Alert Management (AJAX)
```javascript
// Acknowledge an alert
POST /api/ai/acknowledge-alert/
{ "alert_id": 1 }

// Mark alert as restocked
POST /api/ai/mark-restocked/
{ "alert_id": 1 }
```

### View Endpoints
- `/ai/alerts/` - View all restock alerts
- `/ai/consumption-analytics/` - Weekly consumption data
- `/ai/logistics-analytics/` - Deployment metrics & trends
- `/ai/supply-cycle/` - Monthly supply analysis

## 📈 AI Algorithm Details

### Restock Alert Severity Logic

**CRITICAL** (Days to stockout ≤ 3 OR predicted quantity ≤ 0)
- Restock to 5x threshold
- Highest priority action required

**HIGH** (Days to stockout ≤ 7 OR predicted ≤ threshold)
- Restock to 3x threshold
- Should be acted on within 1 week

**MEDIUM** (Predicted ≤ 2x threshold)
- Restock to 2x threshold
- Preventive measure recommended

**LOW** (All others)
- Restock to 1x threshold
- Routine maintenance

### Consumption Trend Analysis
Uses 4-week exponential moving average:
- Weights: [0.4, 0.3, 0.2, 0.1] (recent to oldest)
- Trend classified as STABLE if change < 10%
- INCREASING if > 10% growth
- DECREASING if < 10% decline

### Logistics Efficiency Score
```
Score = (Return Rate % × 0.5) + (On-Time Returns / Total × 50)
Range: 0-100
```

## 🔄 Data Models

### ConsumptionAnalytics
- Stores weekly aggregated consumption data
- One record per item per week
- Includes borrowed items and stock transactions

### RestockAlert
- AI-generated alert for each item when thresholds breach
- Status tracking: ACTIVE → ACKNOWLEDGED → RESTOCKED → RESOLVED
- Includes reasoning, predictions, and recommendations

### SupplyConsumptionCycle
- Monthly summary for each item
- Deployment status classification
- Variance calculations and peak day analysis

### LogisticsAnalytics
- Monthly summary of all borrowing/deployment activities
- Category-wise breakdown
- Efficiency scoring and trending

### Notification
- System notifications for alerts and updates
- User-specific and system-wide messages
- Read/unread tracking with action flags

## 🧪 Testing the System

### Manual Test Steps

1. **Create Test Items**
   - Add 3-5 consumable items with low stock threshold
   - Set different quantities (some high, some low)

2. **Create Stock Transactions**
   - Record stock OUT transactions to simulate consumption
   - Create borrowing records to simulate deployment

3. **Run Weekly Alert Generation**
   ```bash
   python manage.py generate_weekly_alerts
   ```

4. **Check Dashboard**
   - Critical alerts should appear
   - Most consumed items should list correctly

5. **Run Monthly Analytics**
   ```bash
   python manage.py generate_monthly_analytics
   ```

6. **View Analytics Pages**
   - Verify supply cycles are created
   - Check logistics metrics

## ⚙️ Configuration

### Customizing Thresholds

In `core/ai_analytics.py`, modify the `generate_restock_alerts()` method:

```python
if predicted_qty <= 0 or days_until_stockout <= 3:
    severity = 'CRITICAL'
    recommended_restock = int(item.low_stock_threshold * 5)  # Change multiplier
```

### Alert Notification Preferences

In `core/ai_analytics.py`, modify notification creation:

```python
# Currently creates notifications for CRITICAL and HIGH
# Modify to include MEDIUM if desired
if severity in ['CRITICAL', 'HIGH', 'MEDIUM']:
    # Create notification
```

## 📱 Mobile & UI Considerations

- Alert cards are responsive (1 column on mobile, 3 on desktop)
- Quick action buttons for acknowledge/restocked
- Color-coded severity (Red=Critical, Amber=High, etc.)
- Real-time updates via page reload

## 🔐 Security Notes

- All AI endpoints require login
- Only staff can acknowledge alerts
- Activity logging for all alert actions
- CSRF protection on all POST requests

## 📝 Future Enhancements

1. **Predictive ML Models** - Use scikit-learn for demand forecasting
2. **Real-time Notifications** - WebSocket integration for live alerts
3. **Automated Reordering** - Create purchase orders automatically
4. **Budget Optimization** - Factor in costs in restock recommendations
5. **Seasonal Analysis** - Track seasonal consumption patterns
6. **Export Reports** - PDF/Excel exports of analytics

## 🐛 Troubleshooting

### No alerts appearing
- Check if consumption data exists (create test transactions)
- Verify items have category in ['Consumable', 'Medical', 'Safety']
- Run: `python manage.py generate_weekly_alerts`

### Incorrect consumption calculations
- Verify StockTransaction records have correct type and timestamps
- Check Borrowing records are linked to correct items
- Ensure item.low_stock_threshold is set correctly

### Monthly analytics not updating
- Must be run on 1st of month (or manually trigger)
- Command uses previous month's data
- Check LogisticsAnalytics table for records

## 📞 Support

For issues or questions about the AI system, check:
1. Django admin for data validation
2. Console output from management commands
3. Activity logs at `/activity/`
4. Database records in Django admin

---

**System Version**: 1.0
**Last Updated**: May 2026
**Status**: Production Ready ✅
