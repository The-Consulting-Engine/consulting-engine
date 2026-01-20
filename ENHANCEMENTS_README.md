# Consulting Engine MVP v2 - Enhancements

## 🎯 Overview

This document describes the major enhancements implemented in MVP v2 of the Consulting Engine. These features transform the system from a basic diagnostic tool into a sophisticated, context-aware decision engine.

---

## 🆕 What's New in v2

### 1. **Targeted Intake Questions System**

A checkbox-heavy question pack that captures business context and influences initiative selection.

#### Features:
- **12 comprehensive questions** across 5 sections:
  - **Constraints**: Pricing control, menu control, franchise status
  - **Operations**: Scheduling methods, manager autonomy, capacity bottlenecks
  - **Marketing**: Active channels, discount behavior
  - **Goals**: Primary business objective
  - **Risk**: Risk tolerance, data availability

- **Auto-filled defaults** for quick starts
- **Smart effects engine** that:
  - Blacklists irrelevant initiatives
  - Boosts priority of relevant ones
  - Enables/disables sandbox mode
  - Adjusts assumptions based on context

#### Example Flow:
```
User answers: "No pricing control (franchise)"
→ System blacklists: "Pricing Discipline" initiative
→ System adds tag: "franchise_constrained"
```

#### API Endpoints:
- `GET /api/questions/{run_id}/questions` - Get questions + defaults
- `POST /api/questions/{run_id}/responses` - Save responses
- `GET /api/questions/{run_id}/responses` - Get saved responses
- `GET /api/questions/{run_id}/context` - Get derived context

---

### 2. **Specificity Builder**

Every initiative now includes a **concrete action draft** with:

- **What**: Specific action to take
- **Where**: Scope/location/channel/category
- **How Much**: Quantified target or range
- **Timing**: Implementation timeline
- **Next Steps**: 5-7 step checklist
- **Assumptions**: Key assumptions made
- **Data Needed**: Required validation data

#### Specificity Levels:
- **DETAILED**: 4+ concrete fields populated
- **SPECIFIC**: 2-3 concrete fields populated  
- **DIRECTIONAL**: Minimal detail (flagged for user awareness)

#### Context-Aware Generation:
The specificity builder uses intake question responses to customize recommendations:

**Example: Labor Scheduling**
- If scheduling = "manual_fixed":
  - Where: "Focus on peak/off-peak hour staffing (currently using fixed schedules)"
- If scheduling = "software_advanced":
  - Initiative is blacklisted (already optimized)

---

### 3. **Two-Lane Initiative System**

Initiatives now come from TWO lanes:

#### **Lane A: Playbook Initiatives (Primary)**
- Fixed list from vertical configuration
- 8-12 core operational initiatives
- Deterministic eligibility rules
- Proven, low-risk recommendations

#### **Lane B: Sandbox Initiatives (Experimental)**
- **1-2 creative initiatives** per run
- LLM-generated based on context
- Clearly labeled: **🧪 Sandbox / Experimental**
- Includes rationale and validation requirements
- Default to MEDIUM confidence
- Never outranks top playbook initiatives

#### Sandbox Enablement Rules:
```json
{
  "enabled_by_default": false,
  "triggers": [
    "Risk tolerance = moderate OR high",
    "AND marketing channels identified"
  ],
  "max_sandbox_initiatives": 2
}
```

#### Visual Distinction:
- Playbook: Solid border, standard styling
- Sandbox: **Dashed orange border**, experimental badge

---

### 4. **Marketing Plan Schemas**

Marketing initiatives now include **structured plan schemas** with:

- **Channel**: Specific platform or method
- **Target Audience**: Who to reach
- **Timing Window**: Test duration
- **Offer Type**: Promotion or campaign structure
- **Budget Range**: Specific dollar amounts
- **Success Metric**: Clear measurement criteria
- **Test Design**: How to validate
- **Setup Steps**: Detailed implementation checklist

#### Example Marketing Initiatives:

**Local Marketing Experiment**
```json
{
  "channel": "Google Maps, Social Media, or Local Partnerships",
  "target_audience": "Local residents within 3-mile radius",
  "timing_window": "4-week test period",
  "budget_range": "$1000-$2500 for test",
  "success_metric": "Cost per new customer < $25, 20% repeat rate",
  "setup_steps": [
    "Define specific offer and targeting",
    "Set up tracking (promo codes or dedicated landing page)",
    "Run campaign for 4 weeks",
    "Measure new customer acquisition and retention",
    "Calculate ROI and scale if positive"
  ]
}
```

**SMS/Email Reactivation Campaign**
- Targets customers who haven't visited in 60-90 days
- Budget: $500-$1500
- Success: 15% reactivation rate

**Google Maps Conversion Optimization**
- Zero to low budget ($0-$300)
- Focus on profile optimization
- Target: 20% increase in profile views

**Delivery App Menu Optimization**
- Platform-specific menu restructuring
- Budget: $0-$500
- Target: 10% increase in delivery orders

**Promotion Guardrails**
- Internal policy implementation
- Reduce discount rate by 1-2%
- Protect margins while maintaining volume

---

### 5. **Enhanced Vertical Configuration**

Restaurant v1 config now includes:

#### **Question Pack Integration**
```json
{
  "question_id": "pricing_control",
  "effects": {
    "initiative_blacklist": ["rest_pricing_discipline"],
    "tags": ["franchise_constrained"]
  }
}
```

#### **Sandbox Rules**
```json
{
  "sandbox_rules": {
    "enabled_by_default": false,
    "max_sandbox_initiatives": 2,
    "min_risk_tolerance": "moderate",
    "required_conditions": [
      "Marketing channels identified",
      "Risk tolerance moderate or higher"
    ],
    "focus_areas": [
      "Local marketing experiments",
      "Customer engagement tests",
      "Digital channel optimization"
    ]
  }
}
```

#### **Expanded Playbook**
- **13 total initiatives** (up from 7)
- **5 new marketing-focused initiatives**
- All with detailed plan schemas

---

## 🔄 Updated Workflow

```
1. Create Run
   ↓
2. 📋 Answer Intake Questions (NEW!)
   - Auto-filled with sensible defaults
   - Review and adjust as needed
   - Derives context for initiative selection
   ↓
3. Upload CSV Files
   ↓
4. Map Columns
   ↓
5. Confirm Mappings
   ↓
6. Start Analysis
   - Uses question context for filtering
   - Applies blacklists and priority boosts
   - Generates sandbox initiatives if enabled
   - Builds specificity drafts for all initiatives
   ↓
7. ⏸️ MBB Approval Screen (Demo Feature)
   ↓
8. View Results
   - Playbook vs Sandbox clearly distinguished
   - Detailed action plans for each initiative
   - Specificity level indicators
```

---

## 📊 Results Page Enhancements

### Initiative Display:

**Visual Elements:**
- **Lane Badge**: "Playbook" or "🧪 Sandbox / Experimental"
- **Specificity Badge**: DETAILED / SPECIFIC / DIRECTIONAL
- **Dashed Border**: Sandbox initiatives stand out

**Action Plan Section (New!):**
```
╔══════════════════════════════════════════╗
║ Action Plan                              ║
╠══════════════════════════════════════════╣
║ What: Optimize labor scheduling         ║
║ Where/Scope: Peak/off-peak hour staffing║
║ Target: Reduce labor % from 32% to 29%  ║
║ Timing: Implement over 4-6 weeks        ║
║                                          ║
║ Next Steps:                              ║
║ 1. Analyze hourly revenue data          ║
║ 2. Identify peak vs off-peak patterns   ║
║ 3. Create revised schedule template     ║
║ 4. Test schedule for 2 weeks            ║
║ 5. Adjust based on results              ║
║                                          ║
║ Data Needed: Hourly revenue, schedules  ║
╚══════════════════════════════════════════╝
```

---

## 🏗️ Technical Architecture

### New Modules:

#### **Backend:**
```
app/
├── questions/
│   ├── __init__.py
│   ├── processor.py               # Context derivation engine
│   └── restaurant_v1_questions.json
├── initiatives/
│   ├── specificity.py             # Specificity builder
│   ├── selector.py                # Enhanced with sandbox logic
│   └── playbooks/
│       └── restaurant_v1.json     # Updated with marketing initiatives
└── api/
    └── routes/
        └── questions.py           # Questions API
```

#### **Frontend:**
```
src/
├── pages/
│   ├── QuestionsPage.tsx          # NEW: Intake questions UI
│   └── ResultsPage.tsx            # Enhanced with specificity display
└── api/
    └── client.ts                  # Questions API calls
```

### Database Schema Updates:

**New Tables:**
```sql
-- Store question responses
CREATE TABLE question_responses (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES runs(id),
    question_id VARCHAR,
    section VARCHAR,
    response_value JSON
);

-- Store derived context
CREATE TABLE run_contexts (
    id SERIAL PRIMARY KEY,
    run_id INTEGER UNIQUE REFERENCES runs(id),
    constraints JSON,
    operations JSON,
    marketing JSON,
    goals JSON,
    risk JSON,
    derived JSON  -- blacklists, boosts, tags, sandbox_enabled
);
```

**Updated Table:**
```sql
ALTER TABLE initiatives ADD COLUMN specificity_draft JSON;
ALTER TABLE initiatives ADD COLUMN lane VARCHAR DEFAULT 'playbook';
```

---

## 🎮 How to Use

### 1. Start the System
```bash
cd consulting-engine
docker-compose up -d
```

### 2. Create a New Run
- Go to http://localhost:3000
- Click "Create New Run"
- Enter company name and notes
- Select vertical (restaurant_v1)

### 3. **NEW: Answer Questions**
- You'll be taken to the **Intake Questions** page
- Questions are **pre-filled with defaults**
- Review and adjust based on your situation
- Click "Save & Continue"

**Key Questions to Consider:**
- Do you have pricing control? (affects pricing initiatives)
- What marketing channels do you use? (enables sandbox mode)
- What's your risk tolerance? (enables experimental initiatives)
- What's your primary objective? (prioritizes relevant initiatives)

### 4. Upload Data & Map Columns
- Upload your CSV files (PNL, Revenue, Labor)
- Map columns using LLM suggestions
- Confirm mappings

### 5. Start Analysis
- Click "Start Analysis"
- Wait at the "MBB Approval" screen (demo)
- Click "Skip Approval and Continue"

### 6. View Results
- See analytics facts and insights
- Review **playbook initiatives** (solid border)
- Check **sandbox initiatives** (dashed border) if enabled
- Expand action plans for detailed next steps
- Generate reports

---

## 📈 Example: How Context Influences Results

### Scenario 1: Franchise Operator
**Answers:**
- Pricing control: "No control (franchise)"
- Menu control: "No control (fixed menu)"
- Risk tolerance: "Low"

**Result:**
- ❌ Blacklisted: Pricing initiatives, waste reduction
- ❌ Sandbox disabled
- ✅ Focus: Labor scheduling, throughput, overhead reduction

---

### Scenario 2: Independent Restaurant
**Answers:**
- Pricing control: "Full control"
- Marketing channels: "Google Maps, Social Media, Delivery Apps"
- Risk tolerance: "Moderate"

**Result:**
- ✅ All pricing initiatives enabled
- ✅ Sandbox enabled (1-2 marketing experiments)
- ✅ Priority boost: Marketing initiatives
- 🧪 Sandbox ideas: "Local partnership campaign", "SMS reactivation test"

---

## 🔍 Specificity Examples

### High Specificity (DETAILED):
```
Initiative: Optimize Labor Scheduling
What: Align labor hours with demand patterns
Where: Peak/off-peak hours (currently using manual schedules)
How Much: Reduce labor % from 32% to 29% (3% reduction)
Timing: 4-6 weeks implementation
Next Steps: [5 specific steps]
Confidence: MEDIUM
```

### Low Specificity (DIRECTIONAL):
```
Initiative: Experimental Initiative
What: Test new marketing channel
Where: TBD based on available channels
How Much: Budget: $500-2000 test
Timing: TBD
Next Steps: [Generic steps]
Confidence: LOW
```

---

## 🛡️ Guardrails & Constraints

### Initiative Blacklisting:
- System automatically removes irrelevant initiatives
- Example: No pricing control → no pricing initiatives

### Priority Boosting:
- Relevant initiatives get 30% priority boost
- Example: Manual scheduling → labor optimization boosted

### Sandbox Constraints:
- Maximum 2 sandbox initiatives per run
- Only enabled if risk tolerance ≥ moderate
- Never outranks top playbook initiatives (unless HIGH confidence)
- Clearly labeled as experimental

### Specificity Enforcement:
- System labels initiatives with insufficient detail as "DIRECTIONAL"
- Encourages data collection before implementation

---

## 🚀 Benefits

### For Users:
1. **Faster Setup**: Auto-filled questions save time
2. **Relevant Results**: Context-aware filtering removes noise
3. **Actionable Plans**: Step-by-step implementation guides
4. **Experimental Ideas**: Controlled innovation through sandbox
5. **Clear Confidence**: Know what's proven vs. experimental

### For the System:
1. **Scalable**: Question packs easy to add for new verticals
2. **Flexible**: Config-driven behavior changes
3. **Intelligent**: LLM creativity balanced with deterministic guardrails
4. **Transparent**: All logic traceable and explainable

---

## 📚 Configuration Guide

### Adding a New Question:

Edit `backend/app/questions/restaurant_v1_questions.json`:

```json
{
  "question_id": "new_question",
  "section": "Operations",
  "prompt": "How do you handle inventory?",
  "type": "single_select",
  "options": [
    {
      "value": "manual",
      "label": "Manual tracking",
      "effects": {
        "initiative_priority_boost": ["rest_waste_reduction"]
      }
    },
    {
      "value": "software",
      "label": "Inventory software",
      "effects": {}
    }
  ],
  "required": false
}
```

### Adding a New Marketing Initiative:

Edit `backend/app/initiatives/playbooks/restaurant_v1.json`:

```json
{
  "id": "rest_new_marketing",
  "title": "New Marketing Initiative",
  "category": "Marketing",
  "type": "MARKETING",
  "plan_schema": {
    "channel": "Specific channel",
    "target_audience": "Who to reach",
    "timing_window": "Duration",
    "budget_range": "Cost range",
    "success_metric": "How to measure",
    "setup_steps": ["Step 1", "Step 2", "Step 3"]
  },
  "sizing_method": "fixed_value",
  "sizing_params": {
    "low": 5000,
    "mid": 15000,
    "high": 30000
  }
}
```

---

## 🐛 Troubleshooting

### Questions Not Showing:
- Check run was created with correct vertical_id
- Verify questions file exists: `backend/app/questions/restaurant_v1_questions.json`

### Sandbox Initiatives Not Generated:
- Verify risk_tolerance question answered as "moderate" or "high"
- Check marketing_channels question has at least one channel selected
- Confirm LLM is available (OPENAI_API_KEY set)

### Specificity Drafts Missing:
- Check initiative has a valid type (LABOR_OPTIMIZATION, PRICING, etc.)
- Verify run_context was loaded before initiative selection
- Check analytics_facts are available

---

## 📖 Additional Documentation

- **QUICKSTART.md**: Getting started guide
- **ARCHITECTURE.md**: System design details
- **CSV_FORMAT_GUIDE.md**: Data upload requirements
- **ENV_SETUP.md**: Environment configuration

---

## 🎯 Next Steps

### Potential Future Enhancements:
1. **Multi-location support**: Aggregate analysis across locations
2. **Time-series forecasting**: Predict future performance
3. **Benchmark comparisons**: Compare to industry standards
4. **Custom playbooks**: User-defined initiative templates
5. **A/B testing framework**: Track initiative results
6. **Mobile app**: On-the-go diagnostics

---

## 📞 Support

For questions or issues:
1. Check this documentation first
2. Review logs: `docker-compose logs backend`
3. Verify environment variables in `.env`
4. Ensure database is healthy: `docker-compose ps`

---

**System Status**: ✅ All enhancements implemented and running

**Last Updated**: January 19, 2026

**Version**: MVP v2.0
