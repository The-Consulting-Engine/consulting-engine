# Quickstart Guide

Get the Consulting Engine running in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- OpenAI API key

## Steps

### 1. Set Environment Variable

Create a `.env` file in the root directory:

```bash
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

Replace `your_openai_api_key_here` with your actual OpenAI API key.

### 2. Start the System

```bash
docker-compose up --build
```

Wait for all services to start (database, backend, frontend). You'll see:
```
backend_1   | INFO:     Application startup complete.
frontend_1  | ➜  Local:   http://localhost:3000/
```

### 3. Open the Application

Navigate to http://localhost:3000 in your browser.

### 4. Run Sample Diagnostic

1. Click **"New Diagnostic Run"**
2. Enter company name: "Demo Restaurant"
3. Select vertical: "Restaurant Operations"
4. Click **"Create & Start"**

### 5. Upload Sample Data

The system will navigate to the upload page. Upload the sample files:

**Upload 1: P&L Data**
- Select Pack Type: **PNL**
- Choose file: `sample_data/restaurant_pnl_monthly.csv`
- Click **"Upload File"**
- Click **"Map Columns"**
- Review and click **"Confirm Mappings"**

**Upload 2: Revenue Data**
- Select Pack Type: **REVENUE**
- Choose file: `sample_data/restaurant_revenue_pos.csv`
- Click **"Upload File"**
- Click **"Map Columns"**
- Review and click **"Confirm Mappings"**

**Upload 3: Labor Data** (Optional)
- Select Pack Type: **LABOR**
- Choose file: `sample_data/restaurant_labor_payroll.csv`
- Click **"Upload File"**
- Click **"Map Columns"**
- Review and click **"Confirm Mappings"**

### 6. Run Analysis

Once all mappings are confirmed:
1. Click **"Start Analysis"**
2. Wait 30-60 seconds for processing

### 7. View Results

The system will automatically navigate to the results page showing:
- Operating mode and confidence level
- Key metrics with evidence
- Ranked initiatives with impact estimates
- Option to generate reports

### 8. Generate Reports

- Click **"Generate Executive Memo"** for a Markdown report
- Click **"Generate PowerPoint Deck"** for a presentation
- Download reports using the **"Download"** buttons

## Troubleshooting

**Services not starting?**
- Check Docker is running: `docker ps`
- Verify ports 3000, 8000, 5432 are available

**OpenAI API errors?**
- Verify your API key is set correctly in `.env`
- Check you have API credits available

**Database connection errors?**
- Wait 10-15 seconds for PostgreSQL to fully initialize
- Restart with: `docker-compose restart backend`

**Frontend can't connect to backend?**
- Check backend logs: `docker-compose logs backend`
- Verify backend is running: http://localhost:8000/api/health

## Next Steps

- Try uploading your own CSV data
- Review the full [README.md](README.md) for detailed documentation
- Explore vertical configurations in `backend/app/initiatives/playbooks/`
- Customize initiatives for your business type

## Stopping the System

```bash
docker-compose down
```

To remove all data:
```bash
docker-compose down -v
```

---

**Questions?** Check the [API documentation](http://localhost:8000/docs) or review the README.
