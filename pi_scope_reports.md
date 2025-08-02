# PI Scope & Commitment Analysis Reports

## Overview
Advanced reporting suite for tracking PI commitments, scope variance, and unplanned work using label-based feature identification.

## Core Report Categories

### 1. PI Commitment Tracking Reports

#### 1.1 Feature Commitment vs Delivery
**Purpose**: Track delivery against initial PI commitments
```sql
-- PI Feature Commitment Analysis
WITH pi_features AS (
  SELECT 
    key,
    REGEXP_EXTRACT(labels, 'PI-([^,]+)') as pi,
    REGEXP_EXTRACT(labels, 'ART-([^,]+)') as art,
    workstream,
    status,
    created_date,
    resolved_date,
    CASE WHEN created_date <= pi_start_date THEN 'Committed' ELSE 'Added' END as commitment_type
  FROM issues 
  WHERE issuetype = 'Feature' 
    AND labels LIKE '%PI-2024-Q3%'
),
pi_dates AS (
  -- Define PI boundaries (customize dates)
  SELECT 
    'PI-2024-Q3' as pi,
    '2024-07-01' as pi_start_date,
    '2024-09-30' as pi_end_date
)
SELECT 
  pf.art,
  pf.workstream,
  COUNT(CASE WHEN commitment_type = 'Committed' THEN 1 END) as committed_features,
  COUNT(CASE WHEN commitment_type = 'Committed' AND status = 'Done' THEN 1 END) as committed_delivered,
  COUNT(CASE WHEN commitment_type = 'Added' THEN 1 END) as added_features,
  COUNT(CASE WHEN commitment_type = 'Added' AND status = 'Done' THEN 1 END) as added_delivered,
  ROUND(100.0 * COUNT(CASE WHEN commitment_type = 'Committed' AND status = 'Done' THEN 1 END) / 
        NULLIF(COUNT(CASE WHEN commitment_type = 'Committed' THEN 1 END), 0), 1) as commitment_success_rate
FROM pi_features pf
CROSS JOIN pi_dates pd
GROUP BY pf.art, pf.workstream
ORDER BY commitment_success_rate DESC;
```

#### 1.2 PI Objective Achievement Detail
**Purpose**: Map features to PI objectives and track completion
```sql
-- PI Objective Tracking (assumes objective labels like OBJ-1, OBJ-2)
SELECT 
  REGEXP_EXTRACT(labels, 'PI-([^,]+)') as pi,
  REGEXP_EXTRACT(labels, 'OBJ-([^,]+)') as objective,
  COUNT(*) as total_features,
  COUNT(CASE WHEN status = 'Done' THEN 1 END) as completed_features,
  STRING_AGG(key, ', ') as feature_list,
  MIN(created_date) as first_feature_created,
  MAX(resolved_date) as last_feature_completed
FROM issues 
WHERE issuetype = 'Feature' 
  AND labels LIKE '%PI-2024-Q3%'
  AND labels LIKE '%OBJ-%'
GROUP BY 
  REGEXP_EXTRACT(labels, 'PI-([^,]+)'),
  REGEXP_EXTRACT(labels, 'OBJ-([^,]+)')
ORDER BY objective;
```

### 2. Story/Bug/Task Breakdown Analysis

#### 2.1 Feature Decomposition Report
**Purpose**: Analyze story points and work breakdown within committed features
```sql
-- Feature Child Work Analysis
WITH feature_hierarchy AS (
  SELECT 
    f.key as feature_key,
    f.summary as feature_summary,
    REGEXP_EXTRACT(f.labels, 'PI-([^,]+)') as pi,
    f.workstream,
    f.status as feature_status,
    c.key as child_key,
    c.issuetype as child_type,
    c.status as child_status,
    c.story_points,
    c.resolved_date as child_resolved_date
  FROM issues f
  LEFT JOIN issue_links il ON f.key = il.source_key AND il.link_type = 'Epic-Story'
  LEFT JOIN issues c ON il.target_key = c.key
  WHERE f.issuetype = 'Feature' 
    AND f.labels LIKE '%PI-2024-Q3%'
)
SELECT 
  feature_key,
  feature_summary,
  workstream,
  feature_status,
  COUNT(child_key) as total_child_issues,
  COUNT(CASE WHEN child_type = 'Story' THEN 1 END) as story_count,
  COUNT(CASE WHEN child_type = 'Bug' THEN 1 END) as bug_count,
  COUNT(CASE WHEN child_type = 'Task' THEN 1 END) as task_count,
  SUM(story_points) as total_story_points,
  SUM(CASE WHEN child_status = 'Done' THEN story_points ELSE 0 END) as completed_story_points,
  COUNT(CASE WHEN child_status = 'Done' THEN 1 END) as completed_children,
  ROUND(100.0 * COUNT(CASE WHEN child_status = 'Done' THEN 1 END) / NULLIF(COUNT(child_key), 0), 1) as completion_rate
FROM feature_hierarchy
GROUP BY feature_key, feature_summary, workstream, feature_status
ORDER BY total_story_points DESC;
```

#### 2.2 Unplanned Bug Injection Rate
**Purpose**: Track bugs discovered during PI execution vs planned
```sql
-- Bug Injection Analysis
WITH pi_bugs AS (
  SELECT 
    key,
    workstream,
    created_date,
    resolved_date,
    CASE 
      WHEN labels LIKE '%PI-2024-Q3%' THEN 'PI-Labeled'
      WHEN created_date BETWEEN '2024-07-01' AND '2024-09-30' THEN 'PI-Period'
      ELSE 'Outside-PI'
    END as bug_category,
    CASE
      WHEN parent_key IS NOT NULL AND EXISTS (
        SELECT 1 FROM issues p 
        WHERE p.key = parent_key 
        AND p.labels LIKE '%PI-2024-Q3%'
      ) THEN 'Feature-Related'
      ELSE 'Standalone'
    END as bug_type
  FROM issues 
  WHERE issuetype = 'Bug'
    AND (labels LIKE '%PI-2024-Q3%' OR 
         created_date BETWEEN '2024-07-01' AND '2024-09-30')
)
SELECT 
  workstream,
  bug_category,
  bug_type,
  COUNT(*) as bug_count,
  COUNT(CASE WHEN resolved_date IS NOT NULL THEN 1 END) as resolved_bugs,
  AVG(resolved_date - created_date) as avg_resolution_days
FROM pi_bugs
GROUP BY workstream, bug_category, bug_type
ORDER BY workstream, bug_count DESC;
```

### 3. Out-of-Scope Work Detection

#### 3.1 Unplanned Work Analysis
**Purpose**: Identify work completed outside PI commitments
```sql
-- Unplanned Work Detection
WITH pi_period AS (
  SELECT '2024-07-01'::DATE as start_date, '2024-09-30'::DATE as end_date
),
work_classification AS (
  SELECT 
    i.key,
    i.issuetype,
    i.workstream,
    i.summary,
    i.story_points,
    i.created_date,
    i.resolved_date,
    i.labels,
    CASE 
      WHEN i.labels LIKE '%PI-2024-Q3%' THEN 'PI-Committed'
      WHEN i.resolved_date BETWEEN pp.start_date AND pp.end_date THEN 'Unplanned-Delivered'
      WHEN i.created_date BETWEEN pp.start_date AND pp.end_date THEN 'Unplanned-Started'
      ELSE 'Outside-Scope'
    END as work_classification,
    CASE
      WHEN i.issuetype = 'Bug' AND i.priority IN ('Critical', 'High') THEN 'Critical-Bug'
      WHEN i.issuetype = 'Story' AND i.labels LIKE '%Urgent%' THEN 'Urgent-Story'
      WHEN i.issuetype IN ('Task', 'Sub-task') THEN 'Operational'
      ELSE 'Regular'
    END as work_priority_type
  FROM issues i
  CROSS JOIN pi_period pp
  WHERE (i.resolved_date BETWEEN pp.start_date AND pp.end_date
         OR i.labels LIKE '%PI-2024-Q3%')
    AND i.issuetype IN ('Feature', 'Story', 'Bug', 'Task')
)
SELECT 
  workstream,
  work_classification,
  work_priority_type,
  COUNT(*) as issue_count,
  SUM(story_points) as total_story_points,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY workstream), 1) as percentage_of_workstream_work
FROM work_classification
GROUP BY workstream, work_classification, work_priority_type
ORDER BY workstream, work_classification, issue_count DESC;
```

#### 3.2 Capacity Leakage Report
**Purpose**: Measure team capacity spent on unplanned vs planned work
```sql
-- Team Capacity Allocation Analysis
WITH capacity_analysis AS (
  SELECT 
    workstream,
    EXTRACT(WEEK FROM resolved_date) as week_number,
    SUM(CASE WHEN labels LIKE '%PI-2024-Q3%' THEN story_points ELSE 0 END) as planned_points,
    SUM(CASE WHEN labels NOT LIKE '%PI-2024-Q3%' THEN story_points ELSE 0 END) as unplanned_points,
    SUM(story_points) as total_points
  FROM issues 
  WHERE resolved_date BETWEEN '2024-07-01' AND '2024-09-30'
    AND story_points > 0
    AND workstream IS NOT NULL
  GROUP BY workstream, EXTRACT(WEEK FROM resolved_date)
)
SELECT 
  workstream,
  AVG(planned_points) as avg_weekly_planned_points,
  AVG(unplanned_points) as avg_weekly_unplanned_points,
  AVG(total_points) as avg_weekly_total_points,
  ROUND(100.0 * AVG(unplanned_points) / NULLIF(AVG(total_points), 0), 1) as capacity_leakage_percentage,
  ROUND(100.0 * AVG(planned_points) / NULLIF(AVG(total_points), 0), 1) as planned_work_percentage
FROM capacity_analysis
GROUP BY workstream
ORDER BY capacity_leakage_percentage DESC;
```

### 4. PI Scope Variance Analysis

#### 4.1 Scope Change Timeline
**Purpose**: Track when features were added/removed from PI scope
```sql
-- PI Scope Changes Over Time
WITH label_changes AS (
  SELECT 
    cl.issue_key,
    cl.changed_date,
    cl.from_value as old_labels,
    cl.to_value as new_labels,
    CASE 
      WHEN cl.from_value NOT LIKE '%PI-2024-Q3%' AND cl.to_value LIKE '%PI-2024-Q3%' THEN 'Added-to-PI'
      WHEN cl.from_value LIKE '%PI-2024-Q3%' AND cl.to_value NOT LIKE '%PI-2024-Q3%' THEN 'Removed-from-PI'
      ELSE 'Other-Change'
    END as scope_change_type
  FROM changelog cl
  WHERE cl.field = 'labels'
    AND (cl.from_value LIKE '%PI-2024-Q3%' OR cl.to_value LIKE '%PI-2024-Q3%')
),
scope_changes_with_details AS (
  SELECT 
    lc.*,
    i.issuetype,
    i.workstream,
    i.summary,
    i.story_points,
    i.status
  FROM label_changes lc
  JOIN issues i ON lc.issue_key = i.key
  WHERE scope_change_type IN ('Added-to-PI', 'Removed-from-PI')
)
SELECT 
  DATE_TRUNC('week', changed_date) as change_week,
  scope_change_type,
  workstream,
  COUNT(*) as change_count,
  SUM(story_points) as total_story_points_affected,
  STRING_AGG(issue_key || ': ' || summary, '; ') as affected_issues
FROM scope_changes_with_details
GROUP BY DATE_TRUNC('week', changed_date), scope_change_type, workstream
ORDER BY change_week, scope_change_type;
```

#### 4.2 Feature Blocker Impact Analysis
**Purpose**: Analyze how blocked features affect PI delivery
```sql
-- Feature Blocker Impact Analysis
WITH blocked_features AS (
  SELECT 
    f.key as feature_key,
    f.summary,
    f.workstream,
    REGEXP_EXTRACT(f.labels, 'PI-([^,]+)') as pi,
    bl.changed_date as blocked_date,
    un.changed_date as unblocked_date,
    COALESCE(un.changed_date, CURRENT_DATE) - bl.changed_date as blocked_duration_days
  FROM issues f
  LEFT JOIN changelog bl ON f.key = bl.issue_key 
    AND bl.field = 'status' 
    AND bl.to_value = 'Blocked'
  LEFT JOIN changelog un ON f.key = un.issue_key 
    AND un.field = 'status' 
    AND un.from_value = 'Blocked'
    AND un.changed_date > bl.changed_date
  WHERE f.issuetype = 'Feature'
    AND f.labels LIKE '%PI-2024-Q3%'
    AND bl.changed_date IS NOT NULL
)
SELECT 
  workstream,
  COUNT(*) as blocked_features_count,
  AVG(blocked_duration_days) as avg_blocked_days,
  SUM(CASE WHEN unblocked_date IS NULL THEN 1 ELSE 0 END) as still_blocked_count,
  MAX(blocked_duration_days) as max_blocked_days,
  STRING_AGG(feature_key || ' (' || blocked_duration_days || ' days)', ', ') as blocked_feature_details
FROM blocked_features
GROUP BY workstream
ORDER BY avg_blocked_days DESC;
```

### 5. Team Capacity Utilization

#### 5.1 Planned vs Actual Capacity Usage
**Purpose**: Compare planned story point capacity against actual delivery
```sql
-- Team Capacity Utilization Analysis
WITH team_capacity AS (
  -- This would ideally come from team capacity planning data
  SELECT 'Team-Alpha' as workstream, 80 as planned_weekly_capacity
  UNION ALL SELECT 'Team-Beta' as workstream, 60 as planned_weekly_capacity
  UNION ALL SELECT 'Team-Gamma' as workstream, 100 as planned_weekly_capacity
),
weekly_delivery AS (
  SELECT 
    workstream,
    EXTRACT(WEEK FROM resolved_date) as week_number,
    SUM(story_points) as actual_weekly_delivery,
    COUNT(*) as issues_completed
  FROM issues 
  WHERE resolved_date BETWEEN '2024-07-01' AND '2024-09-30'
    AND story_points > 0
    AND workstream IS NOT NULL
  GROUP BY workstream, EXTRACT(WEEK FROM resolved_date)
)
SELECT 
  wd.workstream,
  tc.planned_weekly_capacity,
  AVG(wd.actual_weekly_delivery) as avg_weekly_delivery,
  AVG(wd.issues_completed) as avg_weekly_issues,
  ROUND(100.0 * AVG(wd.actual_weekly_delivery) / tc.planned_weekly_capacity, 1) as capacity_utilization_percentage,
  MIN(wd.actual_weekly_delivery) as min_weekly_delivery,
  MAX(wd.actual_weekly_delivery) as max_weekly_delivery
FROM weekly_delivery wd
JOIN team_capacity tc ON wd.workstream = tc.workstream
GROUP BY wd.workstream, tc.planned_weekly_capacity
ORDER BY capacity_utilization_percentage DESC;
```

## Visualization Recommendations

### Dashboard Layout for PI Scope Reports

**Page 1: PI Commitment Overview**
- PI Objective Achievement Rate (donut chart)
- Committed vs Added Features (stacked bar)
- Scope Change Timeline (line chart)

**Page 2: Work Breakdown Analysis**
- Feature Decomposition Tree (hierarchical view)
- Story Points by Work Type (stacked area)
- Bug Injection Rate Trends (line chart)

**Page 3: Unplanned Work Impact**
- Capacity Leakage by Team (gauge charts)
- Unplanned Work Categories (treemap)
- Blocker Impact Analysis (gantt-style)

**Page 4: Team Performance**
- Planned vs Actual Capacity (bullet charts)
- Team Velocity Consistency (box plots)
- Cross-team Dependency Resolution (network)

## Implementation Notes

1. **Label Hygiene**: Ensure consistent PI labeling across all issues
2. **Parent-Child Relationships**: Maintain Epic-Story links for hierarchy analysis
3. **Story Point Estimation**: Critical for capacity analysis accuracy
4. **Status Workflow**: Standardize status transitions for accurate flow metrics
5. **Date Fields**: Ensure resolved_date is consistently populated