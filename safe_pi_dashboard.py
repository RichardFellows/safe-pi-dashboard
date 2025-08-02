import marimo

__generated_with = "0.9.30"
app = marimo.App(width="medium")


@app.cell
def __():
    """
    # SAFe PI Analytics Dashboard
    
    Interactive dashboard for Scaled Agile program increment metrics using marimo's reactive notebook capabilities.
    """
    import marimo as mo
    import duckdb
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import numpy as np
    from datetime import datetime, timedelta
    import re
    return datetime, duckdb, go, make_subplots, mo, np, pd, px, re, timedelta


@app.cell
def __(duckdb):
    """
    ## Database Connection Setup
    """
    # Initialize DuckDB connection
    # Replace with your actual database path
    conn = duckdb.connect()  # or duckdb.connect("path/to/your/jira.db")
    
    # Test connection and show available tables
    try:
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables] if tables else ["No tables found"]
        print(f"✅ Connected to database. Available tables: {table_names}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        table_names = []
    
    return conn, table_names, tables


@app.cell
def __(conn, mo):
    """
    ## Interactive Controls
    """
    # Get available PIs from the database
    try:
        pi_query = """
        SELECT DISTINCT REGEXP_EXTRACT(labels, 'PI-([^,]+)') as pi
        FROM issues 
        WHERE issuetype = 'Feature' AND labels LIKE '%PI-%'
        ORDER BY pi DESC
        """
        available_pis = [row[0] for row in conn.execute(pi_query).fetchall()]
        available_pis = [f"PI-{pi}" for pi in available_pis if pi]
    except:
        available_pis = ["PI-2024-Q3", "PI-2024-Q4", "PI-2025-Q1"]
    
    # Get available ARTs
    try:
        art_query = """
        SELECT DISTINCT REGEXP_EXTRACT(labels, 'ART-([^,]+)') as art
        FROM issues 
        WHERE issuetype = 'Feature' AND labels LIKE '%ART-%'
        ORDER BY art
        """
        available_arts = [row[0] for row in conn.execute(art_query).fetchall()]
        available_arts = [art for art in available_arts if art]
    except:
        available_arts = ["Platform", "Commerce", "Analytics"]
    
    # Get available workstreams
    try:
        workstream_query = """
        SELECT DISTINCT workstream
        FROM issues 
        WHERE workstream IS NOT NULL AND issuetype = 'Feature'
        ORDER BY workstream
        """
        available_workstreams = [row[0] for row in conn.execute(workstream_query).fetchall()]
    except:
        available_workstreams = ["Team-Alpha", "Team-Beta", "Team-Gamma"]
    
    # Create interactive controls
    selected_pi = mo.ui.dropdown(
        options=available_pis,
        value=available_pis[0] if available_pis else "PI-2024-Q3",
        label="Select PI:"
    )
    
    selected_arts = mo.ui.multiselect(
        options=available_arts,
        value=available_arts,
        label="Select ARTs:"
    )
    
    selected_workstreams = mo.ui.multiselect(
        options=available_workstreams,
        value=available_workstreams,
        label="Select Workstreams:"
    )
    
    refresh_data = mo.ui.button(
        label="🔄 Refresh Data",
        kind="neutral"
    )
    
    # Display controls in a nice layout
    mo.md(f"""
    ### Dashboard Controls
    {mo.hstack([selected_pi, refresh_data])}
    {mo.hstack([selected_arts, selected_workstreams])}
    """)
    return (
        art_query,
        available_arts,
        available_pis,
        available_workstreams,
        pi_query,
        refresh_data,
        selected_arts,
        selected_pi,
        selected_workstreams,
        workstream_query,
    )


@app.cell
def __(conn, mo, selected_arts, selected_pi, selected_workstreams):
    """
    ## Executive Summary Metrics
    """
    # Build filter conditions
    pi_filter = selected_pi.value
    art_filter = "', '".join([f"ART-{art}" for art in selected_arts.value])
    workstream_filter = "', '".join(selected_workstreams.value)
    
    # Executive summary query
    summary_query = f"""
    WITH pi_features AS (
        SELECT 
            key,
            status,
            workstream,
            labels,
            created_date,
            resolved_date
        FROM issues 
        WHERE issuetype = 'Feature' 
          AND labels LIKE '%{pi_filter}%'
          AND workstream IN ('{workstream_filter}')
    ),
    summary_stats AS (
        SELECT 
            COUNT(*) as total_features,
            COUNT(CASE WHEN status = 'Done' THEN 1 END) as completed_features,
            COUNT(CASE WHEN status IN ('In Progress', 'In Review') THEN 1 END) as in_progress_features,
            COUNT(CASE WHEN status = 'To Do' THEN 1 END) as todo_features,
            COUNT(DISTINCT workstream) as active_workstreams
        FROM pi_features
    )
    SELECT 
        total_features,
        completed_features,
        in_progress_features,
        todo_features,
        active_workstreams,
        ROUND(100.0 * completed_features / NULLIF(total_features, 0), 1) as completion_rate
    FROM summary_stats
    """
    
    summary_df = conn.execute(summary_query).df()
    
    if not summary_df.empty:
        summary = summary_df.iloc[0]
        
        # Create summary cards
        completion_rate = summary['completion_rate']
        completion_color = "green" if completion_rate >= 80 else "orange" if completion_rate >= 60 else "red"
        
        summary_cards = mo.md(f"""
        ### 📊 {pi_filter} Executive Summary
        
        {mo.hstack([
            mo.stat(value=str(summary['total_features']), label="Total Features", bordered=True),
            mo.stat(value=str(summary['completed_features']), label="Completed", bordered=True),
            mo.stat(value=f"{completion_rate}%", label="Completion Rate", bordered=True),
            mo.stat(value=str(summary['active_workstreams']), label="Active Teams", bordered=True)
        ])}
        """)
    else:
        summary_cards = mo.md("⚠️ No data available for selected filters")
    
    summary_cards
    return (
        art_filter,
        completion_color,
        completion_rate,
        pi_filter,
        summary,
        summary_cards,
        summary_df,
        summary_query,
        workstream_filter,
    )


@app.cell(kind="sql", query_name="pi_completion_by_art")
def __(art_filter, conn, pi_filter, workstream_filter):
    # PI Feature Completion Rate by ART
    SELECT 
        REGEXP_EXTRACT(labels, 'ART-([^,]+)') as art,
        COUNT(*) as planned_features,
        COUNT(CASE WHEN status = 'Done' THEN 1 END) as completed_features,
        ROUND(100.0 * COUNT(CASE WHEN status = 'Done' THEN 1 END) / COUNT(*), 1) as completion_rate
    FROM issues 
    WHERE issuetype = 'Feature' 
      AND labels LIKE '%{pi_filter}%'
      AND workstream IN ('{workstream_filter}')
      AND REGEXP_EXTRACT(labels, 'ART-([^,]+)') IS NOT NULL
    GROUP BY REGEXP_EXTRACT(labels, 'ART-([^,]+)')
    ORDER BY completion_rate DESC
    return


@app.cell
def __(mo, pi_completion_by_art, pi_filter, px):
    """
    ## PI Completion Rate by ART
    """
    if not pi_completion_by_art.empty:
        fig_completion = px.bar(
            pi_completion_by_art,
            x='completion_rate',
            y='art',
            orientation='h',
            title=f'{pi_filter} Feature Completion Rate by ART',
            labels={'completion_rate': 'Completion Rate (%)', 'art': 'ART'},
            text='completion_rate',
            color='completion_rate',
            color_continuous_scale='RdYlGn'
        )
        
        # Add target line at 80%
        fig_completion.add_vline(
            x=80, 
            line_dash="dash", 
            line_color="red",
            annotation_text="Target: 80%"
        )
        
        fig_completion.update_traces(texttemplate='%{text}%', textposition='outside')
        fig_completion.update_layout(height=max(400, len(pi_completion_by_art) * 50))
        
        mo.ui.plotly(fig_completion)
    else:
        mo.md("⚠️ No ART completion data available")
    return fig_completion,


@app.cell(kind="sql", query_name="workstream_throughput")
def __(conn, pi_filter, workstream_filter):
    # Workstream Throughput Trends
    WITH feature_completions AS (
        SELECT 
            f.workstream,
            DATE_TRUNC('week', c.changed_date) as week,
            COUNT(DISTINCT f.key) as features_completed
        FROM issues f
        JOIN changelog c ON f.key = c.issue_key
        WHERE f.issuetype = 'Feature' 
          AND c.to_status = 'Done'
          AND f.labels LIKE '%{pi_filter}%'
          AND c.changed_date >= CURRENT_DATE - INTERVAL '12 weeks'
          AND f.workstream IN ('{workstream_filter}')
        GROUP BY f.workstream, DATE_TRUNC('week', c.changed_date)
    )
    SELECT 
        workstream,
        week,
        features_completed,
        AVG(features_completed) OVER (
            PARTITION BY workstream 
            ORDER BY week 
            ROWS 3 PRECEDING
        ) as rolling_avg
    FROM feature_completions
    ORDER BY workstream, week
    return


@app.cell
def __(mo, pi_filter, px, workstream_throughput):
    """
    ## Workstream Throughput Trends
    """
    if not workstream_throughput.empty:
        fig_throughput = px.line(
            workstream_throughput,
            x='week',
            y='features_completed',
            color='workstream',
            title=f'{pi_filter} Workstream Feature Throughput Trends',
            labels={'features_completed': 'Features Completed', 'week': 'Week'}
        )
        
        # Add rolling average lines
        for workstream in workstream_throughput['workstream'].unique():
            workstream_data = workstream_throughput[workstream_throughput['workstream'] == workstream]
            fig_throughput.add_scatter(
                x=workstream_data['week'],
                y=workstream_data['rolling_avg'],
                mode='lines',
                name=f'{workstream} (4-week avg)',
                line=dict(dash='dash'),
                opacity=0.7
            )
        
        fig_throughput.update_layout(height=500)
        mo.ui.plotly(fig_throughput)
    else:
        mo.md("⚠️ No throughput data available")
    return fig_throughput, workstream, workstream_data


@app.cell(kind="sql", query_name="lead_time_distribution")
def __(conn, pi_filter, workstream_filter):
    # Feature Lead Time Distribution
    SELECT 
        workstream,
        key,
        (resolved_date - created_date) as lead_time_days,
        PERCENTILE_CONT(0.50) OVER (PARTITION BY workstream) as p50_lead_time,
        PERCENTILE_CONT(0.85) OVER (PARTITION BY workstream) as p85_lead_time
    FROM issues 
    WHERE issuetype = 'Feature' 
      AND status = 'Done'
      AND labels LIKE '%{pi_filter}%'
      AND resolved_date IS NOT NULL
      AND workstream IN ('{workstream_filter}')
    ORDER BY workstream, lead_time_days
    return


@app.cell
def __(lead_time_distribution, mo, pi_filter, px):
    """
    ## Feature Lead Time Distribution
    """
    if not lead_time_distribution.empty:
        fig_lead_time = px.box(
            lead_time_distribution,
            x='workstream',
            y='lead_time_days',
            title=f'{pi_filter} Feature Lead Time Distribution by Workstream',
            labels={'lead_time_days': 'Lead Time (Days)', 'workstream': 'Workstream'}
        )
        
        fig_lead_time.update_layout(
            xaxis_tickangle=-45,
            height=500
        )
        
        mo.ui.plotly(fig_lead_time)
    else:
        mo.md("⚠️ No lead time data available")
    return fig_lead_time,


@app.cell(kind="sql", query_name="pi_burnup_data")
def __(conn, pi_filter):
    # PI Burnup Progress
    WITH pi_scope AS (
        SELECT 
            REGEXP_EXTRACT(labels, 'PI-([^,]+)') as pi,
            COUNT(*) as total_planned
        FROM issues 
        WHERE issuetype = 'Feature' AND labels LIKE '%{pi_filter}%'
        GROUP BY REGEXP_EXTRACT(labels, 'PI-([^,]+)')
    ),
    daily_completions AS (
        SELECT 
            REGEXP_EXTRACT(f.labels, 'PI-([^,]+)') as pi,
            DATE_TRUNC('day', c.changed_date) as completion_date,
            COUNT(*) as features_completed_today
        FROM issues f
        JOIN changelog c ON f.key = c.issue_key
        WHERE f.issuetype = 'Feature' 
          AND c.to_status = 'Done'
          AND f.labels LIKE '%{pi_filter}%'
        GROUP BY REGEXP_EXTRACT(f.labels, 'PI-([^,]+)'), DATE_TRUNC('day', c.changed_date)
    )
    SELECT 
        dc.pi,
        dc.completion_date,
        SUM(dc.features_completed_today) OVER (
            PARTITION BY dc.pi 
            ORDER BY dc.completion_date
        ) as cumulative_completed,
        ps.total_planned
    FROM daily_completions dc
    JOIN pi_scope ps ON dc.pi = ps.pi
    ORDER BY dc.pi, dc.completion_date
    return


@app.cell
def __(go, mo, pd, pi_burnup_data, pi_filter):
    """
    ## PI Burnup Progress
    """
    if not pi_burnup_data.empty:
        fig_burnup = go.Figure()
        
        # Actual progress line
        fig_burnup.add_trace(
            go.Scatter(
                x=pi_burnup_data['completion_date'],
                y=pi_burnup_data['cumulative_completed'],
                mode='lines+markers',
                name='Actual Progress',
                line=dict(color='blue', width=3)
            )
        )
        
        # Ideal burnup line
        start_date = pi_burnup_data['completion_date'].min()
        end_date = pi_burnup_data['completion_date'].max()
        total_planned = pi_burnup_data['total_planned'].iloc[0]
        
        # Create ideal line
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        ideal_progress = [i * total_planned / (len(date_range) - 1) for i in range(len(date_range))]
        
        fig_burnup.add_trace(
            go.Scatter(
                x=date_range,
                y=ideal_progress,
                mode='lines',
                name='Ideal Progress',
                line=dict(color='green', dash='dash', width=2)
            )
        )
        
        # Total planned line
        fig_burnup.add_hline(
            y=total_planned,
            line_dash="dot",
            line_color="red",
            annotation_text=f"Total Planned: {total_planned}"
        )
        
        fig_burnup.update_layout(
            title=f'{pi_filter} Feature Burnup Progress',
            xaxis_title='Date',
            yaxis_title='Cumulative Features Completed',
            hovermode='x unified',
            height=500
        )
        
        mo.ui.plotly(fig_burnup)
    else:
        mo.md("⚠️ No burnup data available")
    return (
        date_range,
        end_date,
        fig_burnup,
        i,
        ideal_progress,
        start_date,
        total_planned,
    )


@app.cell(kind="sql", query_name="cross_art_dependencies")
def __(conn, pi_filter):
    # Cross-ART Dependencies
    WITH art_dependencies AS (
        SELECT 
            REGEXP_EXTRACT(i1.labels, 'ART-([^,]+)') as source_art,
            REGEXP_EXTRACT(i2.labels, 'ART-([^,]+)') as target_art,
            i1.key as source_key,
            i2.key as target_key,
            i2.status as target_status
        FROM issues i1
        JOIN issue_links il ON i1.key = il.source_key
        JOIN issues i2 ON il.target_key = i2.key
        WHERE i1.issuetype = 'Feature' 
          AND i2.issuetype = 'Feature'
          AND i1.labels LIKE '%{pi_filter}%'
          AND i2.labels LIKE '%{pi_filter}%'
          AND REGEXP_EXTRACT(i1.labels, 'ART-([^,]+)') IS NOT NULL
          AND REGEXP_EXTRACT(i2.labels, 'ART-([^,]+)') IS NOT NULL
    )
    SELECT 
        source_art,
        target_art,
        COUNT(*) as dependency_count,
        COUNT(CASE WHEN target_status = 'Done' THEN 1 END) as resolved_dependencies,
        ROUND(100.0 * COUNT(CASE WHEN target_status = 'Done' THEN 1 END) / COUNT(*), 1) as resolution_rate
    FROM art_dependencies
    WHERE source_art != target_art
    GROUP BY source_art, target_art
    ORDER BY dependency_count DESC
    return


@app.cell
def __(cross_art_dependencies, mo, pd, pi_filter, px):
    """
    ## Cross-ART Dependencies
    """
    if not cross_art_dependencies.empty:
        # Create dependency matrix for heatmap
        arts = list(set(cross_art_dependencies['source_art'].tolist() + cross_art_dependencies['target_art'].tolist()))
        matrix = pd.DataFrame(0, index=arts, columns=arts)
        
        for _, row in cross_art_dependencies.iterrows():
            matrix.loc[row['source_art'], row['target_art']] = row['dependency_count']
        
        fig_dependencies = px.imshow(
            matrix,
            title=f'{pi_filter} Cross-ART Dependency Matrix',
            labels={'x': 'Target ART', 'y': 'Source ART', 'color': 'Dependencies'},
            aspect='auto',
            color_continuous_scale='Blues'
        )
        
        # Add text annotations
        for i, source in enumerate(arts):
            for j, target in enumerate(arts):
                if matrix.iloc[i, j] > 0:
                    fig_dependencies.add_annotation(
                        x=j, y=i,
                        text=str(int(matrix.iloc[i, j])),
                        showarrow=False,
                        font=dict(color='white' if matrix.iloc[i, j] > matrix.values.max()/2 else 'black')
                    )
        
        fig_dependencies.update_layout(height=500)
        mo.ui.plotly(fig_dependencies)
    else:
        mo.md("⚠️ No cross-ART dependency data available")
    return arts, fig_dependencies, j, matrix, row


@app.cell(kind="sql", query_name="scope_variance")
def __(conn, pi_filter):
    # Scope Variance Analysis
    WITH pi_features AS (
        SELECT 
            key,
            summary,
            workstream,
            status,
            created_date,
            CASE 
                WHEN created_date <= '2024-07-01' THEN 'Committed'
                ELSE 'Added'
            END as commitment_type
        FROM issues 
        WHERE issuetype = 'Feature' 
          AND labels LIKE '%{pi_filter}%'
    )
    SELECT 
        workstream,
        commitment_type,
        COUNT(*) as feature_count,
        COUNT(CASE WHEN status = 'Done' THEN 1 END) as completed_count,
        ROUND(100.0 * COUNT(CASE WHEN status = 'Done' THEN 1 END) / COUNT(*), 1) as completion_rate
    FROM pi_features
    GROUP BY workstream, commitment_type
    ORDER BY workstream, commitment_type
    return


@app.cell
def __(mo, pi_filter, px, scope_variance):
    """
    ## Scope Variance Analysis
    """
    if not scope_variance.empty:
        fig_scope = px.bar(
            scope_variance,
            x='workstream',
            y='feature_count',
            color='commitment_type',
            title=f'{pi_filter} Committed vs Added Features by Workstream',
            labels={'feature_count': 'Feature Count', 'workstream': 'Workstream'},
            barmode='group'
        )
        
        fig_scope.update_layout(
            xaxis_tickangle=-45,
            height=500
        )
        
        mo.ui.plotly(fig_scope)
    else:
        mo.md("⚠️ No scope variance data available")
    return fig_scope,


@app.cell(kind="sql", query_name="unplanned_work")
def __(conn, pi_filter):
    # Unplanned Work Analysis
    WITH work_classification AS (
        SELECT 
            workstream,
            issuetype,
            CASE 
                WHEN labels LIKE '%{pi_filter}%' THEN 'PI-Committed'
                WHEN resolved_date BETWEEN '2024-07-01' AND '2024-09-30' THEN 'Unplanned-Delivered'
                ELSE 'Outside-Scope'
            END as work_classification,
            story_points
        FROM issues 
        WHERE (resolved_date BETWEEN '2024-07-01' AND '2024-09-30'
               OR labels LIKE '%{pi_filter}%')
          AND issuetype IN ('Feature', 'Story', 'Bug', 'Task')
          AND workstream IS NOT NULL
    )
    SELECT 
        workstream,
        work_classification,
        issuetype,
        COUNT(*) as issue_count,
        SUM(COALESCE(story_points, 0)) as total_story_points
    FROM work_classification
    GROUP BY workstream, work_classification, issuetype
    ORDER BY workstream, work_classification, issue_count DESC
    return


@app.cell
def __(mo, pi_filter, px, unplanned_work):
    """
    ## Unplanned Work Analysis
    """
    if not unplanned_work.empty:
        fig_unplanned = px.treemap(
            unplanned_work,
            path=['workstream', 'work_classification', 'issuetype'],
            values='total_story_points',
            title=f'{pi_filter} Work Classification by Story Points'
        )
        
        fig_unplanned.update_layout(height=600)
        mo.ui.plotly(fig_unplanned)
    else:
        mo.md("⚠️ No unplanned work data available")
    return fig_unplanned,


@app.cell
def __(mo):
    """
    ## Summary & Actions
    
    ### Key Insights
    - Review completion rates against 80% target
    - Monitor scope changes and unplanned work impact
    - Track cross-ART dependencies for coordination
    - Analyze throughput trends for capacity planning
    
    ### Recommended Actions
    1. **Low Completion Rates**: Investigate blockers and resource constraints
    2. **High Unplanned Work**: Review PI planning process and scope management
    3. **Dependency Issues**: Improve cross-ART coordination and communication
    4. **Throughput Variance**: Assess team capacity and workload distribution
    
    ### Next Steps
    - Export data for detailed analysis
    - Schedule PI retrospective meetings
    - Update capacity models for next PI planning
    - Implement process improvements based on findings
    """
    return


@app.cell
def __(mo):
    """
    ## Data Export & Sharing
    """
    export_options = mo.md("""
    ### Export Options
    - **HTML Report**: Use File > Export as HTML for static sharing
    - **Live Dashboard**: Deploy with `marimo run safe_pi_dashboard.py`
    - **PDF Export**: Print page to PDF from browser
    - **Data Tables**: Copy individual query results for further analysis
    """)
    
    export_options
    return export_options,


if __name__ == "__main__":
    app.run()