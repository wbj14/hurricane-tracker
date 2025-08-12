from django.core.management.base import BaseCommand
import subprocess
import sys
import os

class Command(BaseCommand):
    help = "Fetches latest storms by running download_storms.py"

    def handle(self, *args, **options):
        script_path = os.path.join(os.path.dirname(__file__), '../../../download_storms.py')
        script_path = os.path.abspath(script_path)

        if not os.path.exists(script_path):
            self.stderr.write(f"Script not found: {script_path}")
            sys.exit(1)

        self.stdout.write(f"Running: {script_path}")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)

        if result.returncode != 0:
            self.stderr.write(result.stderr)
        else:
            self.stdout.write(result.stdout)
