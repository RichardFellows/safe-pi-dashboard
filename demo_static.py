"""
Static Demo Generator for SAFe PI Dashboard
Creates static HTML exports for GitHub Pages deployment
"""

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime
import json
import os

# Import test data generator
from test_data_generator import JiraTestDataGenerator

class StaticDemoGenerator:
    def __init__(self):
        self.output_dir = "docs"
        self.conn = None
        
    def setup_demo_data(self):
        """Generate demo database"""
        print("🔧 Generating demo data...")
        generator = JiraTestDataGenerator(seed=42)
        self.conn = generator.create_test_database(":memory:")
        print("✅ Demo data ready")
        
    def get_pi_data(self, pi="PI-2024-Q3"):
        """Get data for specific PI"""
        # Executive Summary
        summary_query = f"""
        SELECT 
            COUNT(*) as total_features,
            COUNT(CASE WHEN status = 'Done' THEN 1 END) as completed_features,
            COUNT(CASE WHEN status IN ('In Progress', 'In Review') THEN 1 END) as in_progress_features,
            ROUND(100.0 * COUNT(CASE WHEN status = 'Done' THEN 1 END) / COUNT(*), 1) as completion_rate
        FROM issues 
        WHERE issuetype = 'Feature' AND labels LIKE '%{pi}%'
        """
        
        summary = self.conn.execute(summary_query).fetchone()
        
        return {
            'pi': pi,
            'total_features': summary[0],
            'completed_features': summary[1], 
            'in_progress_features': summary[2],
            'completion_rate': summary[3]
        }
    
    def create_completion_chart(self, pi="PI-2024-Q3"):
        """Create PI completion rate chart"""
        query = f"""
        SELECT 
            REGEXP_EXTRACT(labels, 'ART-([^,]+)') as art,
            COUNT(*) as planned_features,
            COUNT(CASE WHEN status = 'Done' THEN 1 END) as completed_features,
            ROUND(100.0 * COUNT(CASE WHEN status = 'Done' THEN 1 END) / COUNT(*), 1) as completion_rate
        FROM issues 
        WHERE issuetype = 'Feature' 
          AND labels LIKE '%{pi}%'
          AND REGEXP_EXTRACT(labels, 'ART-([^,]+)') IS NOT NULL
        GROUP BY REGEXP_EXTRACT(labels, 'ART-([^,]+)')
        ORDER BY completion_rate DESC
        """
        
        df = self.conn.execute(query).df()
        
        if df.empty:
            return None
            
        fig = px.bar(
            df,
            x='completion_rate',
            y='art',
            orientation='h',
            title=f'{pi} Feature Completion Rate by ART',
            labels={'completion_rate': 'Completion Rate (%)', 'art': 'ART'},
            text='completion_rate',
            color='completion_rate',
            color_continuous_scale='RdYlGn',
            range_color=[0, 100]
        )
        
        # Add target line at 80%
        fig.add_vline(
            x=80, 
            line_dash="dash", 
            line_color="red",
            annotation_text="Target: 80%"
        )
        
        fig.update_traces(texttemplate='%{text}%', textposition='outside')
        fig.update_layout(
            height=400,
            showlegend=False,
            xaxis=dict(range=[0, 105])
        )
        
        return fig
    
    def create_throughput_chart(self, pi="PI-2024-Q3"):
        """Create throughput trends chart"""
        query = f"""
        WITH feature_completions AS (
            SELECT 
                f.workstream,
                DATE_TRUNC('week', c.changed_date) as week,
                COUNT(DISTINCT f.key) as features_completed
            FROM issues f
            JOIN changelog c ON f.key = c.issue_key
            WHERE f.issuetype = 'Feature' 
              AND c.to_status = 'Done'
              AND f.labels LIKE '%{pi}%'
              AND c.changed_date >= CURRENT_DATE - INTERVAL '12 weeks'
              AND f.workstream IS NOT NULL
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
        """
        
        df = self.conn.execute(query).df()
        
        if df.empty:
            return None
            
        fig = px.line(
            df,
            x='week',
            y='features_completed',
            color='workstream',
            title=f'{pi} Workstream Feature Throughput Trends',
            labels={'features_completed': 'Features Completed', 'week': 'Week'}
        )
        
        fig.update_layout(height=500)
        return fig
    
    def create_burnup_chart(self, pi="PI-2024-Q3"):
        """Create PI burnup chart"""
        query = f"""
        WITH pi_scope AS (
            SELECT 
                COUNT(*) as total_planned
            FROM issues 
            WHERE issuetype = 'Feature' AND labels LIKE '%{pi}%'
        ),
        daily_completions AS (
            SELECT 
                DATE_TRUNC('day', c.changed_date) as completion_date,
                COUNT(*) as features_completed_today
            FROM issues f
            JOIN changelog c ON f.key = c.issue_key
            WHERE f.issuetype = 'Feature' 
              AND c.to_status = 'Done'
              AND f.labels LIKE '%{pi}%'
            GROUP BY DATE_TRUNC('day', c.changed_date)
        )
        SELECT 
            dc.completion_date,
            SUM(dc.features_completed_today) OVER (
                ORDER BY dc.completion_date
            ) as cumulative_completed,
            ps.total_planned
        FROM daily_completions dc
        CROSS JOIN pi_scope ps
        ORDER BY dc.completion_date
        """
        
        df = self.conn.execute(query).df()
        
        if df.empty:
            return None
            
        fig = go.Figure()
        
        # Actual progress
        fig.add_trace(
            go.Scatter(
                x=df['completion_date'],
                y=df['cumulative_completed'],
                mode='lines+markers',
                name='Actual Progress',
                line=dict(color='blue', width=3)
            )
        )
        
        # Ideal line
        if not df.empty:
            start_date = df['completion_date'].min()
            end_date = df['completion_date'].max()
            total_planned = df['total_planned'].iloc[0]
            
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            ideal_progress = [i * total_planned / (len(date_range) - 1) for i in range(len(date_range))]
            
            fig.add_trace(
                go.Scatter(
                    x=date_range,
                    y=ideal_progress,
                    mode='lines',
                    name='Ideal Progress',
                    line=dict(color='green', dash='dash', width=2)
                )
            )
        
        fig.update_layout(
            title=f'{pi} Feature Burnup Progress',
            xaxis_title='Date',
            yaxis_title='Cumulative Features Completed',
            height=500
        )
        
        return fig
    
    def create_dependency_chart(self, pi="PI-2024-Q3"):
        """Create dependency matrix"""
        query = f"""
        WITH art_dependencies AS (
            SELECT 
                REGEXP_EXTRACT(i1.labels, 'ART-([^,]+)') as source_art,
                REGEXP_EXTRACT(i2.labels, 'ART-([^,]+)') as target_art,
                i2.status as target_status
            FROM issues i1
            JOIN issue_links il ON i1.key = il.source_key
            JOIN issues i2 ON il.target_key = i2.key
            WHERE i1.issuetype = 'Feature' 
              AND i2.issuetype = 'Feature'
              AND i1.labels LIKE '%{pi}%'
              AND i2.labels LIKE '%{pi}%'
              AND REGEXP_EXTRACT(i1.labels, 'ART-([^,]+)') IS NOT NULL
              AND REGEXP_EXTRACT(i2.labels, 'ART-([^,]+)') IS NOT NULL
        )
        SELECT 
            source_art,
            target_art,
            COUNT(*) as dependency_count
        FROM art_dependencies
        WHERE source_art != target_art
        GROUP BY source_art, target_art
        ORDER BY dependency_count DESC
        """
        
        df = self.conn.execute(query).df()
        
        if df.empty:
            return None
            
        # Create matrix
        arts = list(set(df['source_art'].tolist() + df['target_art'].tolist()))
        matrix = pd.DataFrame(0, index=arts, columns=arts)
        
        for _, row in df.iterrows():
            matrix.loc[row['source_art'], row['target_art']] = row['dependency_count']
        
        fig = px.imshow(
            matrix,
            title=f'{pi} Cross-ART Dependency Matrix',
            labels={'x': 'Target ART', 'y': 'Source ART', 'color': 'Dependencies'},
            aspect='auto',
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(height=400)
        return fig
    
    def generate_static_dashboard(self):
        """Generate complete static dashboard"""
        print("📊 Generating static dashboard...")
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Get data
        pi_data = self.get_pi_data()
        
        # Create charts
        charts = {}
        charts['completion'] = self.create_completion_chart()
        charts['throughput'] = self.create_throughput_chart()
        charts['burnup'] = self.create_burnup_chart()
        charts['dependencies'] = self.create_dependency_chart()
        
        # Generate HTML
        html_content = self.create_html_dashboard(pi_data, charts)
        
        # Write files
        with open(f"{self.output_dir}/index.html", "w") as f:
            f.write(html_content)
        
        print(f"✅ Static dashboard created in {self.output_dir}/")
        return True
    
    def create_html_dashboard(self, pi_data, charts):
        """Create HTML dashboard"""
        
        # Convert charts to HTML
        chart_htmls = {}
        for name, chart in charts.items():
            if chart:
                chart_htmls[name] = pio.to_html(
                    chart, 
                    include_plotlyjs='cdn',
                    div_id=f"chart-{name}",
                    config={'displayModeBar': False}
                )
            else:
                chart_htmls[name] = f"<div id='chart-{name}'>No data available</div>"
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SAFe PI Analytics Dashboard - Demo</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .summary {{
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }}
        .summary h2 {{
            margin: 0 0 15px;
            color: #495057;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .stat {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #007bff;
        }}
        .stat-label {{
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        .chart-section {{
            padding: 30px;
            border-bottom: 1px solid #dee2e6;
        }}
        .chart-section:last-child {{
            border-bottom: none;
        }}
        .chart-section h3 {{
            margin: 0 0 20px;
            color: #495057;
            font-size: 1.5em;
        }}
        .footer {{
            text-align: center;
            padding: 30px;
            background: #f8f9fa;
            color: #6c757d;
        }}
        .footer a {{
            color: #007bff;
            text-decoration: none;
        }}
        .alert {{
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
            padding: 15px;
            border-radius: 4px;
            margin: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SAFe PI Analytics Dashboard</h1>
            <p>Interactive Program Increment Metrics with Marimo & DuckDB</p>
        </div>
        
        <div class="alert">
            <strong>🚀 Live Demo:</strong> This is a static preview generated from test data. 
            The full interactive dashboard supports real-time filtering, drill-downs, and live data connections.
        </div>
        
        <div class="summary">
            <h2>📊 {pi_data['pi']} Executive Summary</h2>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{pi_data['total_features']}</div>
                    <div class="stat-label">Total Features</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{pi_data['completed_features']}</div>
                    <div class="stat-label">Completed</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{pi_data['in_progress_features']}</div>
                    <div class="stat-label">In Progress</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{pi_data['completion_rate']}%</div>
                    <div class="stat-label">Completion Rate</div>
                </div>
            </div>
        </div>
        
        <div class="chart-section">
            <h3>🎯 PI Completion Rate by ART</h3>
            {chart_htmls.get('completion', '<p>No completion data available</p>')}
        </div>
        
        <div class="chart-section">
            <h3>📈 Workstream Throughput Trends</h3>
            {chart_htmls.get('throughput', '<p>No throughput data available</p>')}
        </div>
        
        <div class="chart-section">
            <h3>🔥 PI Burnup Progress</h3>
            {chart_htmls.get('burnup', '<p>No burnup data available</p>')}
        </div>
        
        <div class="chart-section">
            <h3>🔗 Cross-ART Dependencies</h3>
            {chart_htmls.get('dependencies', '<p>No dependency data available</p>')}
        </div>
        
        <div class="footer">
            <p>
                <strong>Ready to get started?</strong><br>
                <a href="https://github.com/RichardFellows/safe-pi-dashboard">
                    📁 View on GitHub
                </a> | 
                <a href="https://marimo.io/">
                    📓 Learn about Marimo
                </a> | 
                <a href="https://duckdb.org/">
                    🦆 Learn about DuckDB
                </a>
            </p>
            <p>
                Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} • 
                <a href="https://github.com/RichardFellows/safe-pi-dashboard/blob/main/LICENSE">MIT License</a>
            </p>
        </div>
    </div>
    
    <script>
        // Add some interactivity
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('SAFe PI Dashboard Demo Loaded');
            
            // Add click tracking for demo purposes
            document.querySelectorAll('a').forEach(link => {{
                link.addEventListener('click', function(e) {{
                    console.log('Link clicked:', this.href);
                }});
            }});
        }});
    </script>
</body>
</html>"""
        
        return html
    
    def run(self):
        """Run complete static demo generation"""
        print("🚀 Starting static demo generation...")
        
        try:
            self.setup_demo_data()
            self.generate_static_dashboard()
            print("✅ Static demo generation complete!")
            return True
        except Exception as e:
            print(f"❌ Static demo generation failed: {e}")
            return False
        finally:
            if self.conn:
                self.conn.close()

if __name__ == "__main__":
    generator = StaticDemoGenerator()
    generator.run()