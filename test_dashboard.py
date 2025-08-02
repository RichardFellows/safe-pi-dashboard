"""
Test Suite for SAFe PI Dashboard
Validates dashboard functionality with mock data
"""

import unittest
import duckdb
import pandas as pd
import tempfile
import os
from datetime import datetime, timedelta
import sys

# Import test data generator
from test_data_generator import JiraTestDataGenerator

class TestSAFePIDashboard(unittest.TestCase):
    """Test cases for SAFe PI Dashboard functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database once for all tests"""
        print("🔧 Setting up test environment...")
        
        # Create temporary database
        cls.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        cls.test_db.close()
        
        # Generate test data
        generator = JiraTestDataGenerator(seed=42)
        cls.conn = generator.create_test_database(cls.test_db.name)
        
        print(f"✅ Test database created: {cls.test_db.name}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database"""
        cls.conn.close()
        os.unlink(cls.test_db.name)
        print("🧹 Test database cleaned up")
    
    def test_database_connection(self):
        """Test that database connection works and has expected tables"""
        # Check tables exist
        tables = self.conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        
        self.assertIn('issues', table_names)
        self.assertIn('changelog', table_names)
        self.assertIn('issue_links', table_names)
        
        # Check basic data
        issue_count = self.conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
        self.assertGreater(issue_count, 0, "Should have issues in test database")
    
    def test_pi_selection_query(self):
        """Test PI selection dropdown data"""
        query = """
        SELECT DISTINCT REGEXP_EXTRACT(labels, 'PI-([^,]+)') as pi
        FROM issues 
        WHERE issuetype = 'Feature' AND labels LIKE '%PI-%'
        ORDER BY pi DESC
        """
        
        result = self.conn.execute(query).fetchall()
        pis = [f"PI-{row[0]}" for row in result if row[0]]
        
        self.assertGreater(len(pis), 0, "Should find PIs in test data")
        self.assertTrue(any('2024-Q3' in pi for pi in pis), "Should contain PI-2024-Q3")
    
    def test_art_selection_query(self):
        """Test ART selection dropdown data"""
        query = """
        SELECT DISTINCT REGEXP_EXTRACT(labels, 'ART-([^,]+)') as art
        FROM issues 
        WHERE issuetype = 'Feature' AND labels LIKE '%ART-%'
        ORDER BY art
        """
        
        result = self.conn.execute(query).fetchall()
        arts = [row[0] for row in result if row[0]]
        
        self.assertGreater(len(arts), 0, "Should find ARTs in test data")
        self.assertIn('Platform', arts, "Should contain Platform ART")
    
    def test_workstream_selection_query(self):
        """Test workstream selection dropdown data"""
        query = """
        SELECT DISTINCT workstream
        FROM issues 
        WHERE workstream IS NOT NULL AND issuetype = 'Feature'
        ORDER BY workstream
        """
        
        result = self.conn.execute(query).fetchall()
        workstreams = [row[0] for row in result]
        
        self.assertGreater(len(workstreams), 0, "Should find workstreams in test data")
    
    def test_executive_summary_query(self):
        """Test executive summary metrics calculation"""
        pi_filter = "PI-2024-Q3"
        workstream_filter = "Team-Alpha', 'Team-Beta', 'Team-Gamma"
        
        query = f"""
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
        
        result = self.conn.execute(query).fetchall()
        self.assertEqual(len(result), 1, "Should return exactly one summary row")
        
        summary = result[0]
        total_features, completed_features, in_progress, todo, workstreams, completion_rate = summary
        
        # Validate data integrity
        self.assertGreaterEqual(total_features, 0)
        self.assertGreaterEqual(completed_features, 0)
        self.assertLessEqual(completed_features, total_features)
        self.assertGreaterEqual(workstreams, 0)
        
        # Validate completion rate calculation
        if total_features > 0:
            expected_rate = round(100.0 * completed_features / total_features, 1)
            self.assertEqual(completion_rate, expected_rate)
    
    def test_pi_completion_by_art_query(self):
        """Test PI completion rate by ART calculation"""
        pi_filter = "PI-2024-Q3"
        workstream_filter = "Team-Alpha', 'Team-Beta"
        
        query = f"""
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
        """
        
        result = self.conn.execute(query).fetchall()
        
        for art, planned, completed, rate in result:
            self.assertIsNotNone(art, "ART should not be null")
            self.assertGreaterEqual(planned, 0)
            self.assertGreaterEqual(completed, 0)
            self.assertLessEqual(completed, planned)
            self.assertGreaterEqual(rate, 0)
            self.assertLessEqual(rate, 100)
    
    def test_workstream_throughput_query(self):
        """Test workstream throughput calculation"""
        pi_filter = "PI-2024-Q3"
        workstream_filter = "Team-Alpha', 'Team-Beta"
        
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
        """
        
        result = self.conn.execute(query).fetchall()
        
        for workstream, week, completed, rolling_avg in result:
            self.assertIsNotNone(workstream)
            self.assertIsNotNone(week)
            self.assertGreaterEqual(completed, 0)
            self.assertGreaterEqual(rolling_avg, 0)
    
    def test_lead_time_distribution_query(self):
        """Test lead time distribution calculation"""
        pi_filter = "PI-2024-Q3"
        workstream_filter = "Team-Alpha', 'Team-Beta"
        
        query = f"""
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
        """
        
        result = self.conn.execute(query).fetchall()
        
        for workstream, key, lead_time, p50, p85 in result:
            self.assertIsNotNone(workstream)
            self.assertIsNotNone(key)
            self.assertGreaterEqual(lead_time, 0, "Lead time should be non-negative")
            self.assertGreaterEqual(p85, p50, "P85 should be >= P50")
    
    def test_pi_burnup_data_query(self):
        """Test PI burnup data calculation"""
        pi_filter = "PI-2024-Q3"
        
        query = f"""
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
        """
        
        result = self.conn.execute(query).fetchall()
        
        if result:  # Only test if we have burnup data
            prev_cumulative = 0
            for pi, date, cumulative, total_planned in result:
                self.assertIsNotNone(pi)
                self.assertIsNotNone(date)
                self.assertGreaterEqual(cumulative, prev_cumulative, "Cumulative should be non-decreasing")
                self.assertLessEqual(cumulative, total_planned, "Cumulative should not exceed planned")
                prev_cumulative = cumulative
    
    def test_cross_art_dependencies_query(self):
        """Test cross-ART dependencies calculation"""
        pi_filter = "PI-2024-Q3"
        
        query = f"""
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
        """
        
        result = self.conn.execute(query).fetchall()
        
        for source_art, target_art, dep_count, resolved, rate in result:
            self.assertIsNotNone(source_art)
            self.assertIsNotNone(target_art)
            self.assertNotEqual(source_art, target_art, "Should only show cross-ART dependencies")
            self.assertGreaterEqual(dep_count, 1)
            self.assertGreaterEqual(resolved, 0)
            self.assertLessEqual(resolved, dep_count)
            self.assertGreaterEqual(rate, 0)
            self.assertLessEqual(rate, 100)
    
    def test_scope_variance_query(self):
        """Test scope variance analysis"""
        pi_filter = "PI-2024-Q3"
        
        query = f"""
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
        """
        
        result = self.conn.execute(query).fetchall()
        
        for workstream, commitment_type, feature_count, completed, rate in result:
            self.assertIsNotNone(workstream)
            self.assertIn(commitment_type, ['Committed', 'Added'])
            self.assertGreaterEqual(feature_count, 1)
            self.assertGreaterEqual(completed, 0)
            self.assertLessEqual(completed, feature_count)
            self.assertGreaterEqual(rate, 0)
            self.assertLessEqual(rate, 100)
    
    def test_data_integrity(self):
        """Test overall data integrity constraints"""
        # Check for required fields
        null_keys = self.conn.execute("SELECT COUNT(*) FROM issues WHERE key IS NULL").fetchone()[0]
        self.assertEqual(null_keys, 0, "No issues should have null keys")
        
        null_types = self.conn.execute("SELECT COUNT(*) FROM issues WHERE issuetype IS NULL").fetchone()[0]
        self.assertEqual(null_types, 0, "No issues should have null issue types")
        
        # Check date consistency
        invalid_dates = self.conn.execute("""
        SELECT COUNT(*) FROM issues 
        WHERE resolved_date IS NOT NULL AND resolved_date < created_date
        """).fetchone()[0]
        self.assertEqual(invalid_dates, 0, "Resolved date should not be before created date")
        
        # Check status consistency
        invalid_status = self.conn.execute("""
        SELECT COUNT(*) FROM issues 
        WHERE status = 'Done' AND resolved_date IS NULL
        """).fetchone()[0]
        self.assertEqual(invalid_status, 0, "Done issues should have resolved dates")
    
    def test_dashboard_filters_work(self):
        """Test that dashboard filters produce different results"""
        # Test different PI filters
        q3_count = self.conn.execute("""
        SELECT COUNT(*) FROM issues 
        WHERE issuetype = 'Feature' AND labels LIKE '%PI-2024-Q3%'
        """).fetchone()[0]
        
        q4_count = self.conn.execute("""
        SELECT COUNT(*) FROM issues 
        WHERE issuetype = 'Feature' AND labels LIKE '%PI-2024-Q4%'
        """).fetchone()[0]
        
        # Should have features in both PIs, but different counts
        self.assertGreater(q3_count, 0, "Should have Q3 features")
        self.assertGreater(q4_count, 0, "Should have Q4 features")
        self.assertNotEqual(q3_count, q4_count, "Different PIs should have different feature counts")
        
        # Test workstream filters
        alpha_count = self.conn.execute("""
        SELECT COUNT(*) FROM issues 
        WHERE workstream = 'Team-Alpha'
        """).fetchone()[0]
        
        beta_count = self.conn.execute("""
        SELECT COUNT(*) FROM issues 
        WHERE workstream = 'Team-Beta'
        """).fetchone()[0]
        
        self.assertGreater(alpha_count, 0, "Should have Team-Alpha issues")
        self.assertGreater(beta_count, 0, "Should have Team-Beta issues")

class TestDashboardIntegration(unittest.TestCase):
    """Integration tests that simulate full dashboard usage"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database for integration tests"""
        cls.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        cls.test_db.close()
        
        generator = JiraTestDataGenerator(seed=123)
        cls.conn = generator.create_test_database(cls.test_db.name)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up integration test database"""
        cls.conn.close()
        os.unlink(cls.test_db.name)
    
    def test_full_dashboard_workflow(self):
        """Test complete dashboard workflow simulation"""
        # 1. Get available PIs (simulating dropdown population)
        pis = self.conn.execute("""
        SELECT DISTINCT REGEXP_EXTRACT(labels, 'PI-([^,]+)') as pi
        FROM issues 
        WHERE issuetype = 'Feature' AND labels LIKE '%PI-%'
        ORDER BY pi DESC
        """).fetchall()
        
        self.assertGreater(len(pis), 0, "Should have available PIs")
        
        # 2. Select a PI (simulating user selection)
        selected_pi = f"PI-{pis[0][0]}"
        
        # 3. Get workstreams for selected PI
        workstreams = self.conn.execute(f"""
        SELECT DISTINCT workstream
        FROM issues 
        WHERE workstream IS NOT NULL 
          AND issuetype = 'Feature'
          AND labels LIKE '%{selected_pi}%'
        ORDER BY workstream
        """).fetchall()
        
        self.assertGreater(len(workstreams), 0, "Should have workstreams for selected PI")
        
        # 4. Generate executive summary
        summary = self.conn.execute(f"""
        SELECT 
            COUNT(*) as total_features,
            COUNT(CASE WHEN status = 'Done' THEN 1 END) as completed_features,
            ROUND(100.0 * COUNT(CASE WHEN status = 'Done' THEN 1 END) / COUNT(*), 1) as completion_rate
        FROM issues 
        WHERE issuetype = 'Feature' AND labels LIKE '%{selected_pi}%'
        """).fetchone()
        
        total, completed, rate = summary
        self.assertGreaterEqual(total, 0)
        self.assertGreaterEqual(completed, 0)
        self.assertLessEqual(completed, total)
        
        # 5. Verify all metric queries work without errors
        metric_queries = [
            # PI completion by ART
            f"""
            SELECT COUNT(*) FROM (
                SELECT 
                    REGEXP_EXTRACT(labels, 'ART-([^,]+)') as art,
                    COUNT(*) as planned_features,
                    COUNT(CASE WHEN status = 'Done' THEN 1 END) as completed_features
                FROM issues 
                WHERE issuetype = 'Feature' 
                  AND labels LIKE '%{selected_pi}%'
                  AND REGEXP_EXTRACT(labels, 'ART-([^,]+)') IS NOT NULL
                GROUP BY REGEXP_EXTRACT(labels, 'ART-([^,]+)')
            )
            """,
            
            # Workstream throughput
            f"""
            SELECT COUNT(*) FROM (
                SELECT 
                    f.workstream,
                    DATE_TRUNC('week', c.changed_date) as week,
                    COUNT(DISTINCT f.key) as features_completed
                FROM issues f
                JOIN changelog c ON f.key = c.issue_key
                WHERE f.issuetype = 'Feature' 
                  AND c.to_status = 'Done'
                  AND f.labels LIKE '%{selected_pi}%'
                  AND c.changed_date >= CURRENT_DATE - INTERVAL '12 weeks'
                  AND f.workstream IS NOT NULL
                GROUP BY f.workstream, DATE_TRUNC('week', c.changed_date)
            )
            """,
            
            # Lead time distribution
            f"""
            SELECT COUNT(*) FROM (
                SELECT 
                    workstream,
                    (resolved_date - created_date) as lead_time_days
                FROM issues 
                WHERE issuetype = 'Feature' 
                  AND status = 'Done'
                  AND labels LIKE '%{selected_pi}%'
                  AND resolved_date IS NOT NULL
                  AND workstream IS NOT NULL
            )
            """
        ]
        
        for i, query in enumerate(metric_queries):
            try:
                result = self.conn.execute(query).fetchone()
                self.assertIsNotNone(result, f"Metric query {i+1} should return result")
            except Exception as e:
                self.fail(f"Metric query {i+1} failed: {e}")
        
        print(f"✅ Full dashboard workflow test passed for {selected_pi}")

def run_dashboard_tests():
    """Main function to run all dashboard tests"""
    print("🧪 Starting SAFe PI Dashboard Test Suite")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestSAFePIDashboard))
    test_suite.addTest(unittest.makeSuite(TestDashboardIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("🎉 All tests passed! Dashboard is functional.")
        print("\n✅ Ready to use dashboard with:")
        print("   marimo edit safe_pi_dashboard.py")
        return True
    else:
        print(f"❌ {len(result.failures)} test(s) failed")
        print(f"❌ {len(result.errors)} error(s) occurred")
        
        if result.failures:
            print("\nFailures:")
            for test, failure in result.failures:
                print(f"  - {test}: {failure}")
        
        if result.errors:
            print("\nErrors:")
            for test, error in result.errors:
                print(f"  - {test}: {error}")
        
        return False

if __name__ == "__main__":
    success = run_dashboard_tests()
    sys.exit(0 if success else 1)