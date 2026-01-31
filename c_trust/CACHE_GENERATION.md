# Data Cache Generation

The C-TRUST backend uses a `data_cache.json` file to serve dashboard data efficiently.

## Automatic Generation (Recommended)

The backend **automatically generates** the cache on first startup if it doesn't exist:

```bash
cd c_trust
python -m uvicorn src.api.main:app --reload --port 8000
```

On first run, you'll see:
```
============================================================
NO DATA CACHE FOUND - GENERATING NOW
This will take a few minutes on first startup...
============================================================
```

The server will start immediately, and the cache will be generated in the background.

## Manual Generation

If you want to regenerate the cache manually (e.g., after data updates):

```bash
cd c_trust
python scripts/update_dashboard_cache.py
```

This runs the same pipeline:
1. **Ingest** - Load all NEST 2.0 study data
2. **Extract** - Extract features from raw data
3. **Calculate** - Compute DQI scores
4. **Cache** - Save to `data_cache.json`

## Cache Contents

The cache contains for each study:
- `overall_score` - DQI score (0-100)
- `risk_level` - Risk assessment (Low/Medium/High/Critical)
- `dimension_scores` - Breakdown by quality dimension
- `features` - Extracted feature values
- `sites` - Site-level summaries with patient data
- `timeline` - Study timeline information
- `last_updated` - Cache timestamp

## Cache Location

- Development: `c_trust/data_cache.json`
- Production: Same location (ensure proper permissions)

## Troubleshooting

**Cache not generating?**
- Check that `DATA_ROOT_PATH` in `.env` points to the NEST data
- Verify NEST data files are accessible
- Check logs for errors during ingestion

**Cache is stale?**
- The backend logs cache age on startup
- Regenerate manually with the script above
- Or delete `data_cache.json` and restart the backend

**Backend slow on startup?**
- This is normal on first run (cache generation)
- Subsequent startups are fast (cache exists)
- Cache generation runs in background, doesn't block API
