#!/usr/bin/env python3
"""
Test Runner for SAFe PI Dashboard
Comprehensive testing suite with multiple validation options
"""

import argparse
import sys
import os
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'duckdb',
        'pandas', 
        'plotly',
        'marimo'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing required packages: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    
    print("✅ All dependencies installed")
    return True

def generate_test_data():
    """Generate test database"""
    print("🔧 Generating test data...")
    
    try:
        from test_data_generator import JiraTestDataGenerator
        
        generator = JiraTestDataGenerator()
        conn = generator.create_test_database("test_jira.db")
        conn.close()
        
        print("✅ Test data generated: test_jira.db")
        return True
    except Exception as e:
        print(f"❌ Failed to generate test data: {e}")
        return False

def run_unit_tests():
    """Run unit tests"""
    print("🧪 Running unit tests...")
    
    try:
        from test_dashboard import run_dashboard_tests
        return run_dashboard_tests()
    except Exception as e:
        print(f"❌ Unit tests failed: {e}")
        return False

def test_marimo_notebook():
    """Test marimo notebook can be parsed and executed"""
    print("📓 Testing marimo notebook...")
    
    dashboard_file = "safe_pi_dashboard.py"
    if not os.path.exists(dashboard_file):
        print(f"❌ Dashboard file not found: {dashboard_file}")
        return False
    
    try:
        # Test if marimo can parse the notebook
        result = subprocess.run(
            ["python", "-c", f"import marimo; app = marimo.load('{dashboard_file}')"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Marimo notebook syntax is valid")
            return True
        else:
            print(f"❌ Marimo notebook has syntax errors: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Marimo notebook test timed out")
        return False
    except FileNotFoundError:
        print("❌ Marimo not installed or not in PATH")
        print("Install with: pip install marimo")
        return False
    except Exception as e:
        print(f"❌ Marimo notebook test failed: {e}")
        return False

def test_sql_queries():
    """Test all SQL queries in isolation"""
    print("📊 Testing SQL queries...")
    
    try:
        import duckdb
        from test_data_generator import JiraTestDataGenerator
        
        # Create temporary test database
        generator = JiraTestDataGenerator()
        conn = generator.create_test_database(":memory:")
        
        # Test queries from the dashboard
        test_queries = {
            "PI Selection": """
                SELECT DISTINCT REGEXP_EXTRACT(labels, 'PI-([^,]+)') as pi
                FROM issues 
                WHERE issuetype = 'Feature' AND labels LIKE '%PI-%'
                ORDER BY pi DESC
            """,
            
            "ART Selection": """
                SELECT DISTINCT REGEXP_EXTRACT(labels, 'ART-([^,]+)') as art
                FROM issues 
                WHERE issuetype = 'Feature' AND labels LIKE '%ART-%'
                ORDER BY art
            """,
            
            "Executive Summary": """
                SELECT 
                    COUNT(*) as total_features,
                    COUNT(CASE WHEN status = 'Done' THEN 1 END) as completed_features,
                    ROUND(100.0 * COUNT(CASE WHEN status = 'Done' THEN 1 END) / COUNT(*), 1) as completion_rate
                FROM issues 
                WHERE issuetype = 'Feature' AND labels LIKE '%PI-2024-Q3%'
            """,
            
            "PI Completion by ART": """
                SELECT 
                    REGEXP_EXTRACT(labels, 'ART-([^,]+)') as art,
                    COUNT(*) as planned_features,
                    COUNT(CASE WHEN status = 'Done' THEN 1 END) as completed_features,
                    ROUND(100.0 * COUNT(CASE WHEN status = 'Done' THEN 1 END) / COUNT(*), 1) as completion_rate
                FROM issues 
                WHERE issuetype = 'Feature' 
                  AND labels LIKE '%PI-2024-Q3%'
                  AND REGEXP_EXTRACT(labels, 'ART-([^,]+)') IS NOT NULL
                GROUP BY REGEXP_EXTRACT(labels, 'ART-([^,]+)')
                ORDER BY completion_rate DESC
            """,
            
            "Workstream Throughput": """
                WITH feature_completions AS (
                    SELECT 
                        f.workstream,
                        DATE_TRUNC('week', c.changed_date) as week,
                        COUNT(DISTINCT f.key) as features_completed
                    FROM issues f
                    JOIN changelog c ON f.key = c.issue_key
                    WHERE f.issuetype = 'Feature' 
                      AND c.to_status = 'Done'
                      AND f.labels LIKE '%PI-2024-Q3%'
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
        }
        
        passed = 0
        failed = 0
        
        for query_name, query in test_queries.items():
            try:
                result = conn.execute(query).fetchall()
                print(f"  ✅ {query_name}: {len(result)} rows")
                passed += 1
            except Exception as e:
                print(f"  ❌ {query_name}: {e}")
                failed += 1
        
        conn.close()
        
        print(f"📊 SQL Tests: {passed} passed, {failed} failed")
        return failed == 0
        
    except Exception as e:
        print(f"❌ SQL query testing failed: {e}")
        return False

def test_dashboard_with_real_data():
    """Test dashboard with generated test data"""
    print("🚀 Testing dashboard with test data...")
    
    if not os.path.exists("test_jira.db"):
        print("❌ Test database not found. Run with --generate-data first.")
        return False
    
    try:
        import duckdb
        
        # Connect to test database and run sample queries
        conn = duckdb.connect("test_jira.db")
        
        # Test database integrity
        tables = conn.execute("SHOW TABLES").fetchall()
        expected_tables = ['issues', 'changelog', 'issue_links']
        
        for table in expected_tables:
            if table not in [t[0] for t in tables]:
                print(f"❌ Missing table: {table}")
                return False
        
        # Test sample dashboard queries
        try:
            # Test PI selection
            pis = conn.execute("""
                SELECT DISTINCT REGEXP_EXTRACT(labels, 'PI-([^,]+)') as pi
                FROM issues 
                WHERE issuetype = 'Feature' AND labels LIKE '%PI-%'
                ORDER BY pi DESC
            """).fetchall()
            
            if not pis:
                print("❌ No PIs found in test data")
                return False
            
            print(f"  ✅ Found {len(pis)} PIs: {[f'PI-{p[0]}' for p in pis[:3]]}")
            
            # Test with first PI
            test_pi = f"PI-{pis[0][0]}"
            
            # Test executive summary
            summary = conn.execute(f"""
                SELECT 
                    COUNT(*) as total_features,
                    COUNT(CASE WHEN status = 'Done' THEN 1 END) as completed_features
                FROM issues 
                WHERE issuetype = 'Feature' AND labels LIKE '%{test_pi}%'
            """).fetchone()
            
            total, completed = summary
            print(f"  ✅ {test_pi}: {completed}/{total} features completed")
            
            # Test ART breakdown
            arts = conn.execute(f"""
                SELECT 
                    REGEXP_EXTRACT(labels, 'ART-([^,]+)') as art,
                    COUNT(*) as count
                FROM issues 
                WHERE issuetype = 'Feature' 
                  AND labels LIKE '%{test_pi}%'
                  AND REGEXP_EXTRACT(labels, 'ART-([^,]+)') IS NOT NULL
                GROUP BY REGEXP_EXTRACT(labels, 'ART-([^,]+)')
            """).fetchall()
            
            if arts:
                print(f"  ✅ Found {len(arts)} ARTs with features")
            
            conn.close()
            print("✅ Dashboard data validation passed")
            return True
            
        except Exception as e:
            print(f"❌ Dashboard query failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def create_demo_script():
    """Create a demo script for users"""
    demo_content = '''#!/usr/bin/env python3
"""
SAFe PI Dashboard Demo Script
Quick start demo with test data
"""

import os
import subprocess
import sys

def main():
    print("🚀 SAFe PI Dashboard Demo")
    print("=" * 40)
    
    # Check if test data exists
    if not os.path.exists("test_jira.db"):
        print("📊 Generating test data...")
        from test_data_generator import JiraTestDataGenerator
        
        generator = JiraTestDataGenerator()
        conn = generator.create_test_database("test_jira.db")
        conn.close()
        print("✅ Test data generated")
    
    # Update dashboard to use test database
    dashboard_file = "safe_pi_dashboard.py"
    if os.path.exists(dashboard_file):
        with open(dashboard_file, 'r') as f:
            content = f.read()
        
        # Replace connection string
        updated_content = content.replace(
            'conn = duckdb.connect()  # or duckdb.connect("path/to/your/jira.db")',
            'conn = duckdb.connect("test_jira.db")'
        )
        
        with open("demo_dashboard.py", 'w') as f:
            f.write(updated_content)
        
        print("✅ Demo dashboard created: demo_dashboard.py")
    
    # Launch dashboard
    print("🌐 Launching dashboard...")
    print("📱 Dashboard will open in your browser")
    print("🔄 Use Ctrl+C to stop the dashboard")
    
    try:
        subprocess.run(["marimo", "run", "demo_dashboard.py"])
    except KeyboardInterrupt:
        print("\\n👋 Dashboard stopped")
    except FileNotFoundError:
        print("❌ Marimo not found. Install with: pip install marimo")
        print("📖 Or run manually: marimo run demo_dashboard.py")

if __name__ == "__main__":
    main()
'''
    
    with open("demo.py", "w") as f:
        f.write(demo_content)
    
    os.chmod("demo.py", 0o755)
    print("✅ Demo script created: demo.py")

def main():
    parser = argparse.ArgumentParser(description="Test runner for SAFe PI Dashboard")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    parser.add_argument("--generate-data", action="store_true", help="Generate test data")
    parser.add_argument("--unit-tests", action="store_true", help="Run unit tests only")
    parser.add_argument("--sql-tests", action="store_true", help="Run SQL tests only")
    parser.add_argument("--marimo-test", action="store_true", help="Test marimo notebook")
    parser.add_argument("--demo", action="store_true", help="Create demo script")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        args.all = True  # Default to all tests
    
    print("🧪 SAFe PI Dashboard Test Runner")
    print("=" * 50)
    
    start_time = time.time()
    all_passed = True
    
    # Check dependencies first
    if not check_dependencies():
        return 1
    
    # Generate test data if requested or if running all tests
    if args.generate_data or args.all:
        if not generate_test_data():
            all_passed = False
    
    # Run SQL tests
    if args.sql_tests or args.all:
        if not test_sql_queries():
            all_passed = False
    
    # Run unit tests
    if args.unit_tests or args.all or args.quick:
        if not run_unit_tests():
            all_passed = False
    
    # Test marimo notebook
    if args.marimo_test or args.all:
        if not test_marimo_notebook():
            all_passed = False
    
    # Test with real data
    if args.all and not args.quick:
        if not test_dashboard_with_real_data():
            all_passed = False
    
    # Create demo script
    if args.demo or args.all:
        create_demo_script()
    
    # Print summary
    elapsed = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"⏱️  Total time: {elapsed:.2f}s")
    
    if all_passed:
        print("🎉 All tests passed! Dashboard is ready to use.")
        print("\n🚀 Quick start:")
        print("   python demo.py                    # Run demo with test data")
        print("   marimo edit safe_pi_dashboard.py  # Edit dashboard")
        print("   marimo run safe_pi_dashboard.py   # Run dashboard as web app")
        return 0
    else:
        print("❌ Some tests failed. Check output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())