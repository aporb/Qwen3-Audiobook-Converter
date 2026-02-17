#!/usr/bin/env python3
"""
Audiobook Converter Suite - Main Entry Point

This script provides a unified interface to all audiobook conversion tools.
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def print_banner():
    """Print the application banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                   Audiobook Converter Suite                   ║
╠═══════════════════════════════════════════════════════════════╣
║  🎧 Convert your books to audiobooks with multiple TTS engines ║
╚═══════════════════════════════════════════════════════════════╝
""")

def print_tools():
    """Print available tools."""
    print("Available Tools:")
    print("\n1. Qwen3 TTS Converter (Local - High Quality)")
    print("   Command: python main.py --tool qwen3 [options]")
    print("   Best for: Local processing with voice cloning")
    
    print("\n2. OpenAI Audiobook (Cloud - Chapter Support)")
    print("   Navigate to: openai-audiobook/ directory")
    print("   Best for: Books with chapter detection")
    
    print("\n3. TTS Reader (Go - Simple CLI)")
    print("   Navigate to: tts-reader/ directory")
    print("   Best for: Quick conversions")
    
    print("\n4. VoxCraft (Web Interface)")
    print("   Navigate to: voxcraft/ directory")
    print("   Best for: GUI-based conversion")
    
    print("\n" + "="*60)

def run_qwen3_converter(args):
    """Run the Qwen3 audiobook converter."""
    try:
        import audiobook_converter
        # Pass through to the converter
        print("Starting Qwen3 Audiobook Converter...")
        print(f"Configuration loaded from: src/config.py")
        print(f"Output directory: audiobooks/")
        print(f"Input directory: book_to_convert/\n")
        
        # Import and run main function if it exists
        if hasattr(audiobook_converter, 'main'):
            audiobook_converter.main()
        else:
            print("Converter loaded. Check src/audiobook_converter.py for usage.")
            print("\nOr run directly:")
            print("  python src/audiobook_converter.py")
    except Exception as e:
        print(f"Error running Qwen3 converter: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    print_banner()
    
    parser = argparse.ArgumentParser(
        description='Audiobook Converter Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Show this help
  python main.py --tool qwen3       # Run Qwen3 converter
  
For other tools, navigate to their directories:
  cd openai-audiobook && python convert.py --help
  cd tts-reader && ./tts-reader --help
  cd voxcraft && docker-compose up
        """
    )
    
    parser.add_argument(
        '--tool',
        choices=['qwen3'],
        help='Select which tool to run (default: show help)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available tools'
    )
    
    args = parser.parse_args()
    
    if args.list or not args.tool:
        print_tools()
        if not args.tool:
            parser.print_help()
        return
    
    if args.tool == 'qwen3':
        run_qwen3_converter(args)

if __name__ == "__main__":
    main()
