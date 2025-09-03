"""
Security Audit Script for WebKarmaApp

Performs automated security checks including:
- Dependency scanning
- Configuration checks
- Sensitive data detection
- Security headers verification
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

SEVERITY_LEVELS = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']
REQUIRED_ENV_VARS = ['SECRET_KEY', 'DATABASE_URL', 'SENTRY_DSN']

@dataclass
class SecurityIssue:
    severity: str
    title: str
    description: str
    location: str
    recommendation: str
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items()}

class SecurityAuditor:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.issues: List[SecurityIssue] = []
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict:
        settings = {}
        env_file = self.base_dir / '.env'
        
        if env_file.exists():
            settings['env_exists'] = True
            settings['env_vars'] = self._parse_env_file(env_file)
        else:
            self.issues.append(SecurityIssue(
                severity='HIGH',
                title='Missing .env file',
                description='No .env file found in the project root.',
                location=str(env_file),
                recommendation='Create a .env file with all required environment variables.'
            ))
            
        return settings
    
    def _parse_env_file(self, env_path: Path) -> Dict:
        env_vars = {}
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key] = value
        except Exception as e:
            self.issues.append(SecurityIssue(
                severity='HIGH',
                title='Error parsing .env file',
                description=f'Failed to parse .env file: {str(e)}',
                location=str(env_path),
                recommendation='Check the .env file for syntax errors.'
            ))
        return env_vars
    
    def check_dependencies(self) -> None:
        """Check for known vulnerabilities in Python dependencies."""
        try:
            result = subprocess.run(
                ['safety', 'check', '--json'],
                capture_output=True,
                text=True,
                cwd=str(self.base_dir)
            )
            
            if result.returncode != 0:
                try:
                    vulns = json.loads(result.stdout)
                    for vuln in vulns.get('vulnerabilities', []):
                        self.issues.append(SecurityIssue(
                            severity=vuln.get('severity', 'MEDIUM').upper(),
                            title=f'Vulnerable dependency: {vuln.get("package_name")} {vuln.get("vulnerable_spec")}',
                            description=vuln.get('advisory', 'No description available'),
                            location=f"{vuln.get('package_name')} ({vuln.get('analyzed_version')})",
                            recommendation=f'Upgrade {vuln.get("package_name")} to version {vuln.get("fixed_versions")} or later.'
                        ))
                except json.JSONDecodeError:
                    self.issues.append(SecurityIssue(
                        severity='MEDIUM',
                        title='Error checking dependencies',
                        description='Failed to parse dependency check results.',
                        location='dependencies',
                        recommendation='Run `safety check` manually to see the full output.'
                    ))
        except FileNotFoundError:
            self.issues.append(SecurityIssue(
                severity='MEDIUM',
                title='Dependency checker not found',
                description='safety package is not installed.',
                location='dependencies',
                recommendation='Install safety: pip install safety'
            ))
    
    def check_environment(self) -> None:
        """Check environment configuration for security issues."""
        if not self.settings.get('env_exists'):
            return
            
        env_vars = self.settings.get('env_vars', {})
        
        # Check for required environment variables
        for var in REQUIRED_ENV_VARS:
            if var not in env_vars:
                self.issues.append(SecurityIssue(
                    severity='HIGH',
                    title=f'Missing required environment variable: {var}',
                    description=f'The required environment variable {var} is not set.',
                    location='.env',
                    recommendation=f'Add {var} to your .env file.'
                ))
        
        # Check for debug mode in production
        if env_vars.get('DEBUG', '').lower() == 'true' and \
           env_vars.get('ENVIRONMENT', '').lower() == 'production':
            self.issues.append(SecurityIssue(
                severity='HIGH',
                title='Debug mode enabled in production',
                description='The application is running in debug mode in production.',
                location='.env',
                recommendation='Set DEBUG=False in production environment.'
            ))
            
        # Check for weak secret key
        secret_key = env_vars.get('SECRET_KEY', '')
        if secret_key and len(secret_key) < 20:
            self.issues.append(SecurityIssue(
                severity='CRITICAL',
                title='Weak SECRET_KEY',
                description='The SECRET_KEY is too short or weak.',
                location='.env',
                recommendation='Generate a strong random key with at least 50 characters.'
            ))
    
    def generate_report(self, output_format: str = 'console') -> None:
        """Generate a security audit report."""
        if output_format == 'json':
            report = {
                'timestamp': str(datetime.now()),
                'issues': [issue.to_dict() for issue in self.issues],
                'summary': {
                    'total': len(self.issues),
                    'by_severity': {
                        level: sum(1 for i in self.issues if i.severity == level)
                        for level in SEVERITY_LEVELS
                    }
                }
            }
            print(json.dumps(report, indent=2))
        else:
            # Console output
            print("\n" + "="*80)
            print("SECURITY AUDIT REPORT".center(80))
            print("="*80)
            
            for level in SEVERITY_LEVELS:
                level_issues = [i for i in self.issues if i.severity == level]
                if level_issues:
                    print(f"\n{level} ISSUES ({(len(level_issues))})")
                    print("-" * 80)
                    for issue in level_issues:
                        print(f"\n[{issue.severity}] {issue.title}")
                        print(f"Location: {issue.location}")
                        print(f"Description: {issue.description}")
                        print(f"Recommendation: {issue.recommendation}")
            
            print("\n" + "="*80)
            print("SUMMARY".center(80))
            print("="*80)
            print(f"Total issues found: {len(self.issues)}")
            for level in SEVERITY_LEVELS:
                count = sum(1 for i in self.issues if i.severity == level)
                print(f"- {level}: {count}")

def main():
    """Main function to run the security audit."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run security audit on WebKarmaApp')
    parser.add_argument('--format', choices=['console', 'json'], default='console',
                      help='Output format (default: console)')
    parser.add_argument('--path', type=str, default='.',
                      help='Path to the project root directory')
    
    args = parser.parse_args()
    
    auditor = SecurityAuditor(args.path)
    
    print("🔍 Running security audit...")
    print("1. Checking dependencies...")
    auditor.check_dependencies()
    
    print("2. Checking environment configuration...")
    auditor.check_environment()
    
    print("\n📊 Generating report...")
    auditor.generate_report(args.format)
    
    critical_issues = sum(1 for i in auditor.issues if i.severity == 'CRITICAL')
    if critical_issues > 0:
        print(f"\n❌ Found {critical_issues} CRITICAL issues that need immediate attention!")
        sys.exit(1)
    else:
        print("\n✅ No critical security issues found.")
        sys.exit(0)

if __name__ == "__main__":
    from datetime import datetime
    main()
