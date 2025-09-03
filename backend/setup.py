from setuptools import setup, find_packages

setup(
    name="karmabot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Core
        'fastapi==0.104.1',
        'uvicorn==0.24.0',
        'python-multipart==0.0.6',
        'python-jose[cryptography]==3.3.0',
        'passlib[bcrypt]==1.7.4',
        'python-dotenv==1.0.0',
        
        # Database
        'sqlalchemy==2.0.23',
        'alembic==1.12.1',
        'psycopg2-binary==2.9.9',
        'asyncpg==0.28.0',
        
        # Redis
        'redis==5.0.1',
        'aioredis==2.0.1',
        
        # Monitoring
        'sentry-sdk[fastapi]==1.35.0',
    ],
    entry_points={
        'console_scripts': [
            'karmabot=app.main:main',
        ],
    },
)
