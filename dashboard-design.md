# SAFe PI Dashboard Design Document

## Overview
Python notebook-based dashboard for Scaled Agile program increment metrics using DuckDB-sourced Jira data.

## Data Architecture

### Source Schema
```sql
-- Primary tables available
issues (key, issuetype, workstream, status, labels, created_date, resolved_date, ...)
changelog (issue_key, field, from_value, to_value, changed_date, ...)
issue_links (source_key, target_key, link_type, ...)
```

### Label Conventions
- PI identification: `PI-YYYY-QN` (e.g., `PI-2024-Q3`)
- ART identification: `ART-{name}` (e.g., `ART-Platform`)
- Feature scope: `issuetype = 'Feature'`

## Core Metrics Specification

### 1. PI Feature Completion Rate
**Purpose**: Track delivery against PI commitments by ART
**Calculation**: 
```sql
SELECT REGEXP_EXTRACT(labels, 'ART-([^,]+)') as art,
       COUNT(*) as planned_features,
       COUNT(CASE WHEN status = 'Done' THEN 1 END) as completed_features,
       ROUND(100.0 * COUNT(CASE WHEN status = 'Done' THEN 1 END) / COUNT(*), 1) as completion_rate
FROM issues 
WHERE issuetype = 'Feature' AND labels LIKE '%PI-2024-Q3%'
GROUP BY REGEXP_EXTRACT(labels, 'ART-([^,]+)');
```
**Visualization**: Horizontal bar chart with target line at 80%

### 2. Workstream Throughput Trends
**Purpose**: Monitor team delivery velocity over time
**Calculation**:
```sql
WITH feature_completions AS (
  SELECT workstream,
         DATE_TRUNC('week', c.changed_date) as week,
         COUNT(DISTINCT f.key) as features_completed
  FROM issues f
  JOIN changelog c ON f.key = c.issue_key
  WHERE f.issuetype = 'Feature' 
    AND c.to_status = 'Done'
    AND f.labels LIKE '%PI-2024-Q3%'
  GROUP BY workstream, DATE_TRUNC('week', c.changed_date)
)
SELECT workstream,
       week,
       features_completed,
       AVG(features_completed) OVER (PARTITION BY workstream ORDER BY week ROWS 3 PRECEDING) as rolling_avg
FROM feature_completions;
```
**Visualization**: Multi-line time series with 4-week rolling average

### 3. Cross-ART Dependency Tracking
**Purpose**: Identify integration risks and coordination needs
**Calculation**:
```sql
SELECT i1_art as source_art,
       i2_art as target_art,
       COUNT(*) as dependency_count,
       COUNT(CASE WHEN i2.status = 'Done' THEN 1 END) as resolved_dependencies
FROM (
  SELECT i1.key as i1_key, REGEXP_EXTRACT(i1.labels, 'ART-([^,]+)') as i1_art,
         i2.key as i2_key, REGEXP_EXTRACT(i2.labels, 'ART-([^,]+)') as i2_art
  FROM issues i1
  JOIN issue_links il ON i1.key = il.source_key
  JOIN issues i2 ON il.target_key = i2.key
  WHERE i1.issuetype = 'Feature' AND i2.issuetype = 'Feature'
    AND i1.labels LIKE '%PI-2024-Q3%'
) deps
JOIN issues i2 ON deps.i2_key = i2.key
WHERE i1_art != i2_art
GROUP BY i1_art, i2_art;
```
**Visualization**: Network diagram or dependency matrix heatmap

### 4. Feature Lead Time Distribution
**Purpose**: Understand flow efficiency and identify bottlenecks
**Calculation**:
```sql
SELECT workstream,
       key,
       resolved_date - created_date as lead_time_days,
       PERCENTILE_CONT(0.50) OVER (PARTITION BY workstream) as p50_lead_time,
       PERCENTILE_CONT(0.85) OVER (PARTITION BY workstream) as p85_lead_time
FROM issues 
WHERE issuetype = 'Feature' 
  AND status = 'Done'
  AND labels LIKE '%PI-2024-Q3%'
  AND resolved_date IS NOT NULL;
```
**Visualization**: Box plots by workstream with percentile annotations

### 5. PI Burnup Progress
**Purpose**: Track cumulative delivery against PI timeline
**Calculation**:
```sql
WITH pi_scope AS (
  SELECT REGEXP_EXTRACT(labels, 'PI-([^,]+)') as pi,
         COUNT(*) as total_planned
  FROM issues 
  WHERE issuetype = 'Feature'
  GROUP BY REGEXP_EXTRACT(labels, 'PI-([^,]+)')
),
daily_completions AS (
  SELECT REGEXP_EXTRACT(f.labels, 'PI-([^,]+)') as pi,
         DATE_TRUNC('day', c.changed_date) as completion_date,
         COUNT(*) as features_completed_today
  FROM issues f
  JOIN changelog c ON f.key = c.issue_key
  WHERE f.issuetype = 'Feature' 
    AND c.to_status = 'Done'
  GROUP BY REGEXP_EXTRACT(f.labels, 'PI-([^,]+)'), DATE_TRUNC('day', c.changed_date)
)
SELECT dc.pi,
       dc.completion_date,
       SUM(dc.features_completed_today) OVER (PARTITION BY dc.pi ORDER BY dc.completion_date) as cumulative_completed,
       ps.total_planned
FROM daily_completions dc
JOIN pi_scope ps ON dc.pi = ps.pi
ORDER BY dc.pi, dc.completion_date;
```
**Visualization**: Line chart with ideal burnup line and actual progress

## Dashboard Layout Design

### Page 1: PI Executive Summary
- **Top Row**: PI completion rates by ART (bar chart)
- **Middle Row**: Overall PI burnup progress (line chart)
- **Bottom Row**: Key metrics cards (total features, completion %, days remaining)

### Page 2: Team Performance Deep Dive
- **Left Column**: Workstream throughput trends (multi-line chart)
- **Right Column**: Lead time distributions (box plots)
- **Bottom**: Team velocity stability metrics (table)

### Page 3: Dependencies & Risk
- **Top**: Cross-ART dependency matrix (heatmap)
- **Bottom Left**: Blocked items by age (bar chart)
- **Bottom Right**: Risk/impediment burndown (line chart)

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Set up Python notebook environment
- Create base SQL queries for top 5 metrics
- Build simple visualizations with matplotlib/plotly

### Phase 2: Interactive Dashboard (Week 3-4)
- Implement parameter controls (PI selection, date ranges)
- Add drill-down capabilities
- Create executive summary views

### Phase 3: Advanced Analytics (Week 5-6)
- Predictive forecasting models
- Statistical trend analysis
- Automated alerting for metric thresholds

## Technical Requirements

### Python Libraries
```python
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st  # for interactivity
import numpy as np
from datetime import datetime, timedelta
```

### Performance Considerations
- Index on `issuetype`, `labels`, `workstream` fields
- Cache metric calculations for 1-hour intervals
- Implement lazy loading for drill-down views
- Use parameterized queries to prevent SQL injection

### Data Refresh Strategy
- Full refresh: Daily at 6 AM
- Incremental updates: Every 4 hours
- Real-time for current sprint data

## Success Metrics
- **Usage**: 80% of POs/SMs accessing weekly
- **Decision Impact**: Reduce PI planning estimation variance by 15%
- **Performance**: All charts load within 3 seconds
- **Accuracy**: <5% variance from manual Jira reports