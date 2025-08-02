# SAFe PI Analytics Dashboard

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Marimo](https://img.shields.io/badge/marimo-0.9.30+-green.svg)](https://marimo.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Interactive dashboard for Scaled Agile Framework (SAFe) Program Increment analytics built with marimo notebooks and DuckDB. Features reactive visualizations, real-time filtering, and comprehensive PI scope analysis.

## Features

🎯 **Executive Summary**: Total features, completion rates, and team metrics  
📊 **PI Completion by ART**: Horizontal bar charts with 80% target lines  
📈 **Workstream Throughput**: Time series with rolling averages  
⏱️ **Lead Time Distribution**: Box plots by workstream  
🔥 **PI Burnup Progress**: Actual vs ideal progress tracking  
🔗 **Cross-ART Dependencies**: Interactive heatmap matrix  
🎲 **Scope Variance**: Committed vs added features analysis  
🚨 **Unplanned Work**: Treemap visualization by story points  

## Quick Start

### 1. Installation
```bash
git clone https://github.com/RichardFellows/safe-pi-dashboard.git
cd safe-pi-dashboard
pip install -r requirements.txt
```

### 2. Run with Test Data
```bash
# Generate demo with test data
python3 run_tests.py --demo
python3 demo.py
```

### 3. Connect Your Data
Update database connection in `safe_pi_dashboard.py` line 33:
```python
conn = duckdb.connect("path/to/your/jira.db")
```

## Data Requirements

Your Jira data should include:
- **Issues table**: `key`, `issuetype`, `status`, `workstream`, `labels`, `created_date`, `resolved_date`
- **Changelog table**: `issue_key`, `field`, `from_value`, `to_value`, `changed_date`
- **Issue Links table**: `source_key`, `target_key`, `link_type`

### Label Format
- **PI Labels**: `PI-YYYY-QN` (e.g., `PI-2024-Q3`)
- **ART Labels**: `ART-{name}` (e.g., `ART-Platform`)
- **Feature Type**: `issuetype = 'Feature'`

## Overview
Comprehensive test validation for the SAFe Program Increment dashboard built with marimo notebooks and DuckDB.

## Files Created

### Core Files
- **`safe_pi_dashboard.py`** - Main marimo dashboard notebook
- **`test_data_generator.py`** - Generates realistic test data
- **`test_dashboard.py`** - Unit and integration tests
- **`run_tests.py`** - Main test runner script

### Documentation
- **`dashboard-design.md`** - Technical design document
- **`pi_scope_reports.md`** - PI scope analysis reports
- **`marimo_notebook_summary.md`** - Marimo documentation summary

## Quick Start Testing

### 1. Install Dependencies
```bash
pip install "marimo[sql]" duckdb pandas plotly numpy
```

### 2. Run Tests
```bash
# Quick validation
python3 run_tests.py --quick

# Full test suite
python3 run_tests.py --all

# Generate test data only
python3 run_tests.py --generate-data

# Create demo
python3 run_tests.py --demo
```

### 3. Test Individual Components
```bash
# Test SQL queries only
python3 run_tests.py --sql-tests

# Test marimo notebook syntax
python3 run_tests.py --marimo-test

# Run unit tests only
python3 run_tests.py --unit-tests
```

## Test Components

### 1. Mock Data Generator (`test_data_generator.py`)
- Generates realistic Jira issues, changelog, and links
- Creates 430+ test issues across multiple PIs and ARTs
- Simulates realistic status transitions and dependencies
- Configurable PI dates and team structures

**Features:**
- **Issues**: Features, Stories, Bugs, Tasks with realistic summaries
- **Labels**: PI-YYYY-QN and ART-{name} format
- **Status Flow**: Realistic progression through workflow states
- **Dependencies**: Cross-ART feature dependencies
- **Scope Changes**: Simulated PI scope variance

### 2. Unit Tests (`test_dashboard.py`)
- **Database Connection**: Validates table structure and data
- **Query Validation**: Tests all SQL queries for syntax and logic
- **Data Integrity**: Checks date consistency and referential integrity
- **Filter Testing**: Validates PI and workstream filtering
- **Metric Calculations**: Verifies completion rates and throughput

**Test Categories:**
- Executive summary metrics
- PI completion rates by ART
- Workstream throughput trends
- Lead time distributions
- Cross-ART dependencies
- Scope variance analysis

### 3. Integration Tests
- **Full Workflow**: Simulates complete user interaction
- **Reactive Updates**: Tests filter changes and data refresh
- **Performance**: Validates query execution times
- **Error Handling**: Tests graceful degradation

### 4. Test Runner (`run_tests.py`)
- **Dependency Checks**: Verifies required packages
- **Multiple Test Modes**: Quick, full, and component-specific
- **Demo Creation**: Generates ready-to-run demo script
- **Results Summary**: Clear pass/fail reporting

## Test Data Structure

### Generated Data Volume
- **50 Features** across 3 PIs and 4 ARTs
- **200 Stories** (60% linked to features)
- **80 Bugs** with realistic priorities
- **100 Tasks** for operational work
- **500+ Changelog entries** for status transitions
- **Cross-ART dependencies** for integration testing

### Realistic Patterns
- **Completion Rates**: Varying by PI (Q2: 70%, Q3: 50%, Q4: 15%)
- **Status Distribution**: Realistic workflow progression
- **Date Consistency**: Created < Resolved dates
- **Label Hygiene**: Proper PI and ART labeling

## Validation Checks

### SQL Query Validation
- ✅ PI selection dropdown population
- ✅ ART and workstream filtering
- ✅ Executive summary calculations
- ✅ Completion rate formulas
- ✅ Throughput trend analysis
- ✅ Lead time distributions
- ✅ Burnup progress tracking
- ✅ Cross-ART dependency matrix

### Data Integrity Checks
- ✅ No null keys or issue types
- ✅ Resolved dates after created dates
- ✅ Done status has resolved dates
- ✅ Completion rates between 0-100%
- ✅ Cumulative metrics non-decreasing

### Dashboard Functionality
- ✅ Marimo notebook syntax validation
- ✅ Interactive controls population
- ✅ Reactive filter updates
- ✅ Chart generation without errors
- ✅ Export capabilities

## Running Dashboard with Test Data

### Option 1: Demo Script
```bash
python3 run_tests.py --demo
python3 demo.py
```

### Option 2: Manual Setup
```bash
# Generate test data
python3 -c "from test_data_generator import JiraTestDataGenerator; g=JiraTestDataGenerator(); g.create_test_database('test_jira.db')"

# Update dashboard connection (line 33 in safe_pi_dashboard.py)
# Change: conn = duckdb.connect()
# To: conn = duckdb.connect("test_jira.db")

# Run dashboard
marimo edit safe_pi_dashboard.py
```

## Expected Test Results

When tests pass, you should see:
- ✅ All dependencies installed
- ✅ Test data generated (430+ issues)
- ✅ SQL queries execute without errors
- ✅ Data integrity constraints satisfied
- ✅ Marimo notebook syntax valid
- ✅ Dashboard functionality confirmed

## Troubleshooting

### Common Issues
1. **Missing Dependencies**: Install with `pip install "marimo[sql]" duckdb pandas plotly`
2. **Python Version**: Requires Python 3.8+
3. **Database Path**: Ensure correct path in dashboard connection
4. **Marimo Not Found**: Install with `pip install marimo`

### Debug Mode
```bash
# Run with verbose output
python3 test_dashboard.py -v

# Check specific SQL query
python3 -c "from test_dashboard import *; # run individual test"
```

## Performance Benchmarks

Test data generation and validation typically completes in:
- **Data Generation**: ~2-3 seconds
- **Unit Tests**: ~5-10 seconds
- **Full Test Suite**: ~15-20 seconds
- **Dashboard Load**: ~1-2 seconds

This validates the dashboard will perform well with real Jira data of similar size.