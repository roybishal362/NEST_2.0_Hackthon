#!/usr/bin/env python3
"""
C-TRUST Main Application Entry Point
====================================

Clinical AI System (C-TRUST) - Main application launcher
Provides command-line interface for system operations.
"""

import click
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core import initialize_core_system, get_logger, config_manager


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """C-TRUST Clinical AI System - Command Line Interface"""
    pass


@cli.command()
@click.option('--config', '-c', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
def init(config, verbose):
    """Initialize the C-TRUST system"""
    click.echo("🏥 Initializing C-TRUST Clinical AI System...")
    
    try:
        # Initialize core system
        success = initialize_core_system()
        
        if success:
            click.echo("✅ C-TRUST system initialized successfully!")
            
            # Display system information
            config_obj = config_manager.get_config()
            click.echo(f"📊 Database: {config_obj.database_url}")
            click.echo(f"🤖 Agents configured: {len(config_obj.agent_configs)}")
            click.echo(f"🛡️  Guardian Agent: {'Enabled' if config_obj.guardian_enabled else 'Disabled'}")
            
        else:
            click.echo("❌ Failed to initialize C-TRUST system")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Initialization error: {e}")
        sys.exit(1)


@cli.command()
@click.option('--port', '-p', default=8501, help='Dashboard port')
@click.option('--host', '-h', default='localhost', help='Dashboard host')
def dashboard(port, host):
    """Launch the C-TRUST dashboard"""
    click.echo(f"🚀 Starting C-TRUST dashboard on {host}:{port}")
    
    try:
        # Import and run Streamlit dashboard
        import subprocess
        import os
        
        # Set environment variables
        os.environ['STREAMLIT_SERVER_PORT'] = str(port)
        os.environ['STREAMLIT_SERVER_ADDRESS'] = host
        
        # Launch Streamlit
        dashboard_path = Path(__file__).parent / "src" / "dashboard" / "app.py"
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(dashboard_path),
            "--server.port", str(port),
            "--server.address", host
        ])
        
    except Exception as e:
        click.echo(f"❌ Failed to start dashboard: {e}")
        sys.exit(1)


@cli.command()
@click.argument('data_path', type=click.Path(exists=True))
@click.option('--study-id', '-s', help='Specific study ID to process')
@click.option('--batch-size', '-b', default=1000, help='Batch processing size')
def process(data_path, study_id, batch_size):
    """Process clinical trial data"""
    click.echo(f"📊 Processing clinical data from: {data_path}")
    
    if study_id:
        click.echo(f"🎯 Processing specific study: {study_id}")
    
    try:
        # Initialize system first
        initialize_core_system()
        
        # Import and run data processing
        from src.data.ingestion import DataIngestionEngine
        
        engine = DataIngestionEngine()
        
        with click.progressbar(length=100, label='Processing data') as bar:
            # This would be implemented in the data ingestion task
            click.echo("\n⚠️  Data processing engine not yet implemented")
            click.echo("📋 This will be implemented in task 2: Data ingestion and processing pipeline")
        
    except Exception as e:
        click.echo(f"❌ Processing error: {e}")
        sys.exit(1)


@cli.command()
def status():
    """Check C-TRUST system status"""
    click.echo("🔍 Checking C-TRUST system status...")
    
    try:
        # Initialize and check system health
        initialize_core_system()
        
        from src.core import db_manager
        
        # Database health check
        db_healthy = db_manager.health_check()
        click.echo(f"💾 Database: {'✅ Healthy' if db_healthy else '❌ Unhealthy'}")
        
        # Configuration status
        config = config_manager.get_config()
        click.echo(f"⚙️  Configuration: ✅ Loaded")
        click.echo(f"🤖 Agents: {len(config.agent_configs)} configured")
        
        # Guardian status
        guardian_status = "✅ Enabled" if config.guardian_enabled else "⚠️  Disabled"
        click.echo(f"🛡️  Guardian Agent: {guardian_status}")
        
        click.echo("\n📊 System Status: ✅ Operational")
        
    except Exception as e:
        click.echo(f"❌ Status check failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--component', '-c', help='Specific component to test')
@click.option('--property', '-p', is_flag=True, help='Run property-based tests')
def test(component, property):
    """Run C-TRUST test suite"""
    click.echo("🧪 Running C-TRUST test suite...")
    
    try:
        import subprocess
        
        # Build pytest command
        cmd = [sys.executable, "-m", "pytest", "tests/"]
        
        if component:
            cmd.extend(["-k", component])
        
        if property:
            cmd.extend(["-m", "property"])
            click.echo("🔬 Running property-based tests...")
        
        cmd.extend(["-v", "--tb=short"])
        
        # Run tests
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            click.echo("✅ All tests passed!")
        else:
            click.echo("❌ Some tests failed")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Test execution failed: {e}")
        sys.exit(1)


@cli.command()
def config():
    """Display current configuration"""
    click.echo("⚙️  C-TRUST Configuration:")
    
    try:
        config_obj = config_manager.get_config()
        
        click.echo(f"\n📊 Database Configuration:")
        click.echo(f"  URL: {config_obj.database_url}")
        click.echo(f"  Batch Size: {config_obj.batch_size}")
        click.echo(f"  Max Jobs: {config_obj.max_concurrent_jobs}")
        
        click.echo(f"\n🤖 Agent Configuration:")
        for name, agent_config in config_obj.agent_configs.items():
            status = "✅" if agent_config.enabled else "❌"
            click.echo(f"  {status} {agent_config.name}: weight={agent_config.weight}")
        
        click.echo(f"\n📈 DQI Configuration:")
        dqi = config_obj.dqi_config
        for dimension, weight in dqi.weights.items():
            click.echo(f"  {dimension.title()}: {weight*100}%")
        
        click.echo(f"\n🛡️  Guardian Configuration:")
        click.echo(f"  Enabled: {'✅' if config_obj.guardian_enabled else '❌'}")
        click.echo(f"  Sensitivity: {config_obj.guardian_sensitivity}")
        
    except Exception as e:
        click.echo(f"❌ Failed to display configuration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()