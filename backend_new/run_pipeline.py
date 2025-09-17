#!/usr/bin/env python3
"""
Launcher script for the job application pipeline with email tracking.

This script provides a simple way to launch the pipeline with or without the email
tracking server in a single command.
"""

import argparse
import os
import sys
import subprocess


def main():
    parser = argparse.ArgumentParser(description="Launch job application pipeline with optional email tracking")
    
    parser.add_argument("--resume", type=str, help="Path to your resume file (txt, md, pdf, docx)")
    parser.add_argument("--title", type=str, default="", help="Job title filter")
    parser.add_argument("--location", type=str, default="United States", help="Job location filter")
    parser.add_argument("--interactive", action="store_true", help="Collect input via interactive prompts")
    parser.add_argument("--dry-run", action="store_true", help="Skip sending emails, just log actions")
    
    parser.add_argument("--tracker", action="store_true", help="Launch email tracker server after pipeline")
    parser.add_argument("--tracker-only", action="store_true", help="Launch only the email tracker server")
    parser.add_argument("--port", type=int, default=8001, help="Port for email tracker server")
    
    args = parser.parse_args()
    
    # Determine the path to the main pipeline script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pipeline_script = os.path.join(script_dir, "job_application_pipeline.py")
    
    if args.tracker_only:
        # Launch only the email tracker using the pipeline script
        cmd = [
            sys.executable,
            pipeline_script,
            "--email-tracker",
            "--email-tracker-port", str(args.port)
        ]
        print("🚀 Launching email tracker server only...")
    else:
        # Build the pipeline command with all options
        cmd = [sys.executable, pipeline_script]
        
        if args.resume:
            cmd.extend(["--resume", args.resume])
        if args.title:
            cmd.extend(["--title", args.title])
        if args.location:
            cmd.extend(["--location", args.location])
        if args.interactive:
            cmd.append("--interactive")
        if args.dry_run:
            cmd.append("--dry-run")
        
        # Add email tracker if requested
        if args.tracker:
            cmd.append("--email-tracker")
            cmd.extend(["--email-tracker-port", str(args.port)])
        
        print("🚀 Launching job application pipeline...")
    
    # Execute the command
    try:
        process = subprocess.Popen(cmd)
        process.wait()
    except KeyboardInterrupt:
        print("\n⏹️ Process interrupted by user")
    except Exception as e:
        print(f"⚠️ Error running pipeline: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
