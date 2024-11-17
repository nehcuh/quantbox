import PyInstaller.__main__
import os

def build_executable():
    """Build the executable for QuantBox"""
    
    # Get the absolute path to the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Define the entry point
    entry_point = os.path.join(project_root, 'quantbox', 'savers', 'data_saver.py')
    
    # Define the output directory
    dist_path = os.path.join(project_root, 'dist')
    
    # Create settings directory if it doesn't exist
    settings_dir = os.path.join(project_root, 'quantbox', 'settings')
    os.makedirs(settings_dir, exist_ok=True)
    
    # PyInstaller options
    options = [
        entry_point,  # Entry point script
        '--name=quantbox',  # Name of the executable
        '--onefile',  # Create a single executable file
        '--console',  # Show console window for debugging
        f'--distpath={dist_path}',  # Output directory
        '--clean',  # Clean PyInstaller cache
        '--hidden-import=pymongo',
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=gm',
        '--hidden-import=tushare',
    ]
    
    # Run PyInstaller
    PyInstaller.__main__.run(options)

if __name__ == '__main__':
    build_executable()
