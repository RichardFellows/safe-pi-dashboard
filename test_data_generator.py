"""
Test Data Generator for SAFe PI Dashboard
Creates realistic mock Jira data for testing dashboard functionality
"""

import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import uuid

class JiraTestDataGenerator:
    def __init__(self, seed=42):
        """Initialize test data generator with reproducible seed"""
        random.seed(seed)
        np.random.seed(seed)
        
        # Configuration
        self.pis = ['PI-2024-Q2', 'PI-2024-Q3', 'PI-2024-Q4']
        self.arts = ['Platform', 'Commerce', 'Analytics', 'Mobile']
        self.workstreams = [
            'Team-Alpha', 'Team-Beta', 'Team-Gamma', 'Team-Delta',
            'Team-Echo', 'Team-Foxtrot', 'Team-Golf', 'Team-Hotel'
        ]
        self.statuses = ['To Do', 'In Progress', 'In Review', 'Done', 'Blocked']
        self.issue_types = ['Feature', 'Story', 'Bug', 'Task', 'Sub-task']
        self.priorities = ['Critical', 'High', 'Medium', 'Low']
        
        # Date ranges for different PIs
        self.pi_dates = {
            'PI-2024-Q2': (datetime(2024, 4, 1), datetime(2024, 6, 30)),
            'PI-2024-Q3': (datetime(2024, 7, 1), datetime(2024, 9, 30)),
            'PI-2024-Q4': (datetime(2024, 10, 1), datetime(2024, 12, 31))
        }
    
    def generate_issue_key(self, issue_type, index):
        """Generate realistic Jira issue keys"""
        prefixes = {
            'Feature': 'FEAT',
            'Story': 'STORY',
            'Bug': 'BUG',
            'Task': 'TASK',
            'Sub-task': 'SUB'
        }
        return f"{prefixes.get(issue_type, 'ISSUE')}-{index:04d}"
    
    def generate_realistic_summary(self, issue_type, pi, art):
        """Generate realistic issue summaries"""
        feature_templates = [
            "Implement {feature} for {domain}",
            "Add {capability} to {system}",
            "Enhance {component} with {functionality}",
            "Create {service} integration",
            "Develop {feature} dashboard"
        ]
        
        story_templates = [
            "As a user, I want to {action} so that {benefit}",
            "Implement {component} API endpoint",
            "Add validation for {field}",
            "Create unit tests for {module}",
            "Update documentation for {feature}"
        ]
        
        bug_templates = [
            "Fix {component} memory leak",
            "Resolve {system} timeout issues",
            "Correct {feature} validation logic",
            "Address {service} error handling",
            "Fix {ui} display issues"
        ]
        
        # Domain-specific terms
        domains = {
            'Platform': ['authentication', 'infrastructure', 'monitoring', 'deployment'],
            'Commerce': ['checkout', 'payment', 'catalog', 'inventory'],
            'Analytics': ['reporting', 'metrics', 'dashboards', 'data pipeline'],
            'Mobile': ['iOS app', 'Android app', 'push notifications', 'offline sync']
        }
        
        features = ['user management', 'data export', 'real-time sync', 'performance optimization']
        components = ['API', 'database', 'UI component', 'service', 'module']
        
        if issue_type == 'Feature':
            template = random.choice(feature_templates)
            return template.format(
                feature=random.choice(features),
                domain=random.choice(domains.get(art, domains['Platform'])),
                capability=random.choice(['search', 'filtering', 'sorting', 'pagination']),
                system=f"{art} system",
                component=random.choice(components),
                functionality=random.choice(['caching', 'validation', 'security', 'monitoring']),
                service=f"{art.lower()} service"
            )
        elif issue_type == 'Story':
            template = random.choice(story_templates)
            return template.format(
                action=random.choice(['view reports', 'export data', 'filter results', 'save preferences']),
                benefit=random.choice(['better visibility', 'improved efficiency', 'easier access', 'enhanced security']),
                component=random.choice(components),
                field=random.choice(['email', 'password', 'date', 'amount']),
                module=random.choice(['authentication', 'validation', 'reporting', 'integration']),
                feature=random.choice(domains.get(art, domains['Platform']))
            )
        elif issue_type == 'Bug':
            template = random.choice(bug_templates)
            return template.format(
                component=random.choice(components),
                system=f"{art} system",
                feature=random.choice(domains.get(art, domains['Platform'])),
                service=f"{art.lower()} service",
                ui=random.choice(['form', 'table', 'chart', 'modal'])
            )
        else:
            return f"{issue_type} for {art} {pi}"
    
    def generate_labels(self, pi, art, issue_type):
        """Generate realistic label combinations"""
        labels = [pi, f"ART-{art}"]
        
        # Add objective labels for features
        if issue_type == 'Feature':
            obj_num = random.randint(1, 5)
            labels.append(f"OBJ-{obj_num}")
        
        # Add component labels
        components = ['backend', 'frontend', 'database', 'api', 'integration']
        if random.random() < 0.6:  # 60% chance
            labels.append(random.choice(components))
        
        # Add priority labels occasionally
        if random.random() < 0.3:  # 30% chance
            labels.append('urgent')
        
        return ', '.join(labels)
    
    def generate_story_points(self, issue_type):
        """Generate realistic story point estimates"""
        if issue_type == 'Feature':
            return None  # Features typically don't have story points
        elif issue_type == 'Story':
            return random.choices([1, 2, 3, 5, 8, 13], weights=[20, 30, 25, 15, 8, 2])[0]
        elif issue_type == 'Bug':
            return random.choices([1, 2, 3, 5], weights=[40, 30, 20, 10])[0]
        elif issue_type in ['Task', 'Sub-task']:
            return random.choices([1, 2, 3], weights=[50, 30, 20])[0]
        return None
    
    def generate_dates(self, pi, status):
        """Generate realistic created and resolved dates"""
        pi_start, pi_end = self.pi_dates[pi]
        
        # Created date - features mostly created before PI, others during
        if random.random() < 0.7:  # 70% created in PI timeframe
            created_date = pi_start + timedelta(
                days=random.randint(0, (pi_end - pi_start).days)
            )
        else:  # 30% created before PI (pre-planned)
            created_date = pi_start - timedelta(days=random.randint(1, 60))
        
        # Resolved date based on status
        resolved_date = None
        if status == 'Done':
            # Resolved sometime after creation, within PI timeframe
            min_days = 1
            max_days = min(30, (pi_end - created_date).days)
            if max_days > min_days:
                resolved_date = created_date + timedelta(
                    days=random.randint(min_days, max_days)
                )
        
        return created_date, resolved_date
    
    def generate_issues(self, num_features=50, num_stories=200, num_bugs=80, num_tasks=100):
        """Generate main issues table"""
        issues = []
        issue_index = 1
        
        # Generate Features
        for i in range(num_features):
            pi = random.choice(self.pis)
            art = random.choice(self.arts)
            workstream = random.choice(self.workstreams)
            
            # Features have higher completion rates in earlier PIs
            if pi == 'PI-2024-Q2':
                status = random.choices(self.statuses, weights=[5, 10, 10, 70, 5])[0]
            elif pi == 'PI-2024-Q3':
                status = random.choices(self.statuses, weights=[10, 20, 15, 50, 5])[0]
            else:  # PI-2024-Q4
                status = random.choices(self.statuses, weights=[30, 30, 20, 15, 5])[0]
            
            created_date, resolved_date = self.generate_dates(pi, status)
            
            issue = {
                'key': self.generate_issue_key('Feature', issue_index),
                'issuetype': 'Feature',
                'summary': self.generate_realistic_summary('Feature', pi, art),
                'status': status,
                'priority': random.choice(self.priorities),
                'workstream': workstream,
                'labels': self.generate_labels(pi, art, 'Feature'),
                'story_points': self.generate_story_points('Feature'),
                'created_date': created_date,
                'resolved_date': resolved_date,
                'parent_key': None
            }
            issues.append(issue)
            issue_index += 1
        
        # Generate Stories (some linked to features)
        for i in range(num_stories):
            pi = random.choice(self.pis)
            art = random.choice(self.arts)
            workstream = random.choice(self.workstreams)
            status = random.choices(self.statuses, weights=[15, 25, 15, 40, 5])[0]
            
            # Some stories belong to features
            parent_key = None
            if random.random() < 0.6:  # 60% linked to features
                feature_issues = [iss for iss in issues if iss['issuetype'] == 'Feature' and pi in iss['labels']]
                if feature_issues:
                    parent_key = random.choice(feature_issues)['key']
            
            created_date, resolved_date = self.generate_dates(pi, status)
            
            issue = {
                'key': self.generate_issue_key('Story', issue_index),
                'issuetype': 'Story',
                'summary': self.generate_realistic_summary('Story', pi, art),
                'status': status,
                'priority': random.choice(self.priorities),
                'workstream': workstream,
                'labels': self.generate_labels(pi, art, 'Story'),
                'story_points': self.generate_story_points('Story'),
                'created_date': created_date,
                'resolved_date': resolved_date,
                'parent_key': parent_key
            }
            issues.append(issue)
            issue_index += 1
        
        # Generate Bugs
        for i in range(num_bugs):
            pi = random.choice(self.pis)
            art = random.choice(self.arts)
            workstream = random.choice(self.workstreams)
            
            # Bugs have different status distribution
            status = random.choices(self.statuses, weights=[20, 30, 10, 35, 5])[0]
            
            created_date, resolved_date = self.generate_dates(pi, status)
            
            issue = {
                'key': self.generate_issue_key('Bug', issue_index),
                'issuetype': 'Bug',
                'summary': self.generate_realistic_summary('Bug', pi, art),
                'status': status,
                'priority': random.choices(self.priorities, weights=[10, 30, 40, 20])[0],
                'workstream': workstream,
                'labels': self.generate_labels(pi, art, 'Bug'),
                'story_points': self.generate_story_points('Bug'),
                'created_date': created_date,
                'resolved_date': resolved_date,
                'parent_key': None
            }
            issues.append(issue)
            issue_index += 1
        
        # Generate Tasks
        for i in range(num_tasks):
            pi = random.choice(self.pis)
            art = random.choice(self.arts)
            workstream = random.choice(self.workstreams)
            status = random.choices(self.statuses, weights=[10, 20, 10, 55, 5])[0]
            
            created_date, resolved_date = self.generate_dates(pi, status)
            
            issue = {
                'key': self.generate_issue_key('Task', issue_index),
                'issuetype': 'Task',
                'summary': self.generate_realistic_summary('Task', pi, art),
                'status': status,
                'priority': random.choice(self.priorities),
                'workstream': workstream,
                'labels': self.generate_labels(pi, art, 'Task'),
                'story_points': self.generate_story_points('Task'),
                'created_date': created_date,
                'resolved_date': resolved_date,
                'parent_key': None
            }
            issues.append(issue)
            issue_index += 1
        
        return pd.DataFrame(issues)
    
    def generate_changelog(self, issues_df):
        """Generate changelog entries for status transitions"""
        changelog = []
        
        for _, issue in issues_df.iterrows():
            created_date = issue['created_date']
            resolved_date = issue['resolved_date']
            current_status = issue['status']
            
            # Generate realistic status progression
            status_flow = ['To Do', 'In Progress', 'In Review', 'Done']
            
            if current_status == 'Blocked':
                # Blocked issues have different flow
                transitions = ['To Do', 'In Progress', 'Blocked']
            else:
                # Find how far through the flow this issue got
                if current_status in status_flow:
                    end_index = status_flow.index(current_status)
                    transitions = status_flow[:end_index + 1]
                else:
                    transitions = ['To Do', current_status]
            
            # Generate changelog entries for each transition
            current_date = created_date
            for i, status in enumerate(transitions):
                if i == 0:
                    # Initial creation
                    changelog.append({
                        'issue_key': issue['key'],
                        'field': 'status',
                        'from_value': None,
                        'to_value': status,
                        'changed_date': current_date
                    })
                else:
                    # Status transitions
                    if resolved_date and status == 'Done':
                        transition_date = resolved_date
                    else:
                        # Random date between current and resolved (or PI end)
                        max_date = resolved_date if resolved_date else current_date + timedelta(days=30)
                        days_diff = (max_date - current_date).days
                        if days_diff > 0:
                            transition_date = current_date + timedelta(
                                days=random.randint(1, max(1, days_diff))
                            )
                        else:
                            transition_date = current_date + timedelta(days=1)
                    
                    changelog.append({
                        'issue_key': issue['key'],
                        'field': 'status',
                        'from_value': transitions[i-1],
                        'to_value': status,
                        'changed_date': transition_date
                    })
                    current_date = transition_date
            
            # Add some label changes (scope changes)
            if random.random() < 0.15:  # 15% of issues have label changes
                label_change_date = created_date + timedelta(
                    days=random.randint(1, 14)
                )
                
                old_labels = issue['labels']
                # Simulate PI scope changes
                if 'PI-2024-Q3' in old_labels and random.random() < 0.5:
                    new_labels = old_labels.replace('PI-2024-Q3', 'PI-2024-Q4')
                else:
                    new_labels = old_labels + ', urgent'
                
                changelog.append({
                    'issue_key': issue['key'],
                    'field': 'labels',
                    'from_value': old_labels,
                    'to_value': new_labels,
                    'changed_date': label_change_date
                })
        
        return pd.DataFrame(changelog)
    
    def generate_issue_links(self, issues_df):
        """Generate issue links for dependencies"""
        links = []
        
        features = issues_df[issues_df['issuetype'] == 'Feature']
        stories = issues_df[issues_df['issuetype'] == 'Story']
        
        # Epic-Story links
        for _, story in stories.iterrows():
            if story['parent_key']:
                links.append({
                    'source_key': story['parent_key'],
                    'target_key': story['key'],
                    'link_type': 'Epic-Story'
                })
        
        # Feature dependencies (cross-ART)
        for _, feature in features.iterrows():
            if random.random() < 0.3:  # 30% of features have dependencies
                # Find potential dependency targets (different ART)
                feature_art = None
                for label in feature['labels'].split(', '):
                    if label.startswith('ART-'):
                        feature_art = label
                        break
                
                if feature_art:
                    other_features = features[
                        (features['key'] != feature['key']) & 
                        (~features['labels'].str.contains(feature_art, na=False))
                    ]
                    
                    if not other_features.empty:
                        target = other_features.sample(1).iloc[0]
                        links.append({
                            'source_key': feature['key'],
                            'target_key': target['key'],
                            'link_type': 'Dependency'
                        })
        
        return pd.DataFrame(links)
    
    def create_test_database(self, db_path=":memory:"):
        """Create complete test database with all tables"""
        print("🚀 Generating test data...")
        
        # Generate data
        issues_df = self.generate_issues()
        changelog_df = self.generate_changelog(issues_df)
        links_df = self.generate_issue_links(issues_df)
        
        print(f"✅ Generated {len(issues_df)} issues")
        print(f"✅ Generated {len(changelog_df)} changelog entries")
        print(f"✅ Generated {len(links_df)} issue links")
        
        # Create database
        conn = duckdb.connect(db_path)
        
        # Create and populate tables
        conn.execute("CREATE TABLE issues AS SELECT * FROM issues_df")
        conn.execute("CREATE TABLE changelog AS SELECT * FROM changelog_df")
        conn.execute("CREATE TABLE issue_links AS SELECT * FROM links_df")
        
        print(f"✅ Created test database at {db_path}")
        
        # Print summary statistics
        self.print_data_summary(conn)
        
        return conn
    
    def print_data_summary(self, conn):
        """Print summary of generated test data"""
        print("\n📊 Test Data Summary:")
        print("=" * 40)
        
        # Issues by type
        result = conn.execute("""
        SELECT issuetype, COUNT(*) as count 
        FROM issues 
        GROUP BY issuetype 
        ORDER BY count DESC
        """).fetchall()
        
        print("Issues by Type:")
        for issue_type, count in result:
            print(f"  {issue_type}: {count}")
        
        # Issues by PI
        result = conn.execute("""
        SELECT 
            REGEXP_EXTRACT(labels, 'PI-([^,]+)') as pi,
            COUNT(*) as count 
        FROM issues 
        WHERE labels LIKE '%PI-%'
        GROUP BY REGEXP_EXTRACT(labels, 'PI-([^,]+)')
        ORDER BY pi
        """).fetchall()
        
        print("\nFeatures by PI:")
        for pi, count in result:
            print(f"  PI-{pi}: {count}")
        
        # Completion rates
        result = conn.execute("""
        SELECT 
            REGEXP_EXTRACT(labels, 'PI-([^,]+)') as pi,
            COUNT(*) as total,
            COUNT(CASE WHEN status = 'Done' THEN 1 END) as completed,
            ROUND(100.0 * COUNT(CASE WHEN status = 'Done' THEN 1 END) / COUNT(*), 1) as completion_rate
        FROM issues 
        WHERE issuetype = 'Feature' AND labels LIKE '%PI-%'
        GROUP BY REGEXP_EXTRACT(labels, 'PI-([^,]+)')
        ORDER BY pi
        """).fetchall()
        
        print("\nFeature Completion Rates:")
        for pi, total, completed, rate in result:
            print(f"  PI-{pi}: {completed}/{total} ({rate}%)")

if __name__ == "__main__":
    # Generate test database
    generator = JiraTestDataGenerator()
    conn = generator.create_test_database("test_jira.db")
    
    print("\n🎯 Test database created successfully!")
    print("Usage: Update your dashboard connection to use 'test_jira.db'")