#!/usr/bin/env python3
"""Interactive configuration wizard for Serbian Data MCP Server.

This script helps users set up their config.json file with helpful prompts
and validation.
"""

import json
import sys
from pathlib import Path


def print_header():
    """Print wizard header."""
    print("🇷🇸 Serbian Data MCP Server - Configuration Wizard")
    print("=" * 55)
    print()


def get_yes_no(prompt, default=True):
    """Get yes/no response from user."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not response:
            return default
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("   Please enter 'y' or 'n'")


def get_validated_input(prompt, validator, default, error_message):
    """Get input with validation."""
    while True:
        try:
            response = input(f"{prompt} [{default}]: ").strip()
            if not response:
                response = default

            result = validator(response)
            return result
        except ValueError:
            print(f"   ❌ {error_message}")


def validate_url(url):
    """Validate URL format."""
    if not url.startswith(('http://', 'https://')):
        raise ValueError("URL must start with http:// or https://")
    return url


def validate_float(value):
    """Validate float value."""
    try:
        f = float(value)
        if f <= 0:
            raise ValueError("Value must be positive")
        return f
    except ValueError:
        raise ValueError("Please enter a valid number")


def validate_int(value):
    """Validate integer value."""
    try:
        i = int(value)
        if i <= 0:
            raise ValueError("Value must be positive")
        return i
    except ValueError:
        raise ValueError("Please enter a valid integer")


def validate_path(path):
    """Validate directory path."""
    # Convert to Path and check if valid
    p = Path(path)
    # Don't check existence - it might be created later
    if any(c in p.name for c in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']):
        raise ValueError("Path contains invalid characters")
    return str(p)


def main():
    """Run configuration wizard."""
    print_header()

    print("This wizard will help you configure the Serbian Data MCP Server.")
    print("You can press Enter to accept the default values shown in brackets.")
    print()

    # Check for existing config
    config_path = Path("config.json")
    existing_config = {}

    if config_path.exists():
        print("ℹ️  Found existing config.json")
        if get_yes_no("Load existing configuration as defaults?", True):
            try:
                with open(config_path) as f:
                    existing_config = json.load(f)
                print("   ✅ Loaded existing configuration")
            except (json.JSONDecodeError, IOError) as e:
                print(f"   ⚠️  Could not load existing config: {e}")
        print()

    # Collect configuration
    config = {}

    print("📡 API Settings")
    print("-" * 55)

    config['api_base'] = get_validated_input(
        "API base URL",
        validate_url,
        existing_config.get('api_base', 'https://data.gov.rs'),
        "Please enter a valid URL starting with http:// or https://"
    )

    config['rate_limit'] = get_validated_input(
        "Rate limit (seconds between requests)",
        validate_float,
        existing_config.get('rate_limit', 1.0),
        "Please enter a positive number"
    )

    config['timeout'] = get_validated_input(
        "Request timeout (seconds)",
        validate_int,
        existing_config.get('timeout', 30),
        "Please enter a positive integer"
    )

    print()
    print("📁 Directory Settings")
    print("-" * 55)

    config['cache_dir'] = get_validated_input(
        "Cache directory",
        validate_path,
        existing_config.get('cache_dir', '.cache'),
        "Please enter a valid directory name"
    )

    config['export_dir'] = get_validated_input(
        "Export directory (for charts and downloads)",
        validate_path,
        existing_config.get('export_dir', 'exports'),
        "Please enter a valid directory name"
    )

    print()
    print("📋 Configuration Summary")
    print("-" * 55)
    print(json.dumps(config, indent=2))
    print()

    # Confirm and save
    if get_yes_no("Save this configuration?", True):
        # Create backup if exists
        if config_path.exists():
            backup_path = config_path.with_suffix('.json.backup')
            print(f"   ℹ️  Backing up existing config to {backup_path.name}")
            config_path.rename(backup_path)

        # Save new config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        print("   ✅ Configuration saved to config.json")

        # Create directories
        print()
        print("📁 Creating directories...")
        try:
            Path(config['cache_dir']).mkdir(exist_ok=True)
            print(f"   ✅ Created cache directory: {config['cache_dir']}")
        except Exception as e:
            print(f"   ⚠️  Could not create cache directory: {e}")

        try:
            Path(config['export_dir']).mkdir(exist_ok=True)
            print(f"   ✅ Created export directory: {config['export_dir']}")
        except Exception as e:
            print(f"   ⚠️  Could not create export directory: {e}")

        print()
        print("🎉 Configuration complete!")
        print()
        print("Next steps:")
        print("  1. Test the connection: ./test_connection.sh")
        print("  2. Run the server: python -m serbian_data_mcp")
        print("  3. Try examples: python example_usage.py")
    else:
        print("❌ Configuration cancelled. No changes saved.")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print()
        print("⚠️  Configuration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
