#!/usr/bin/env python3
"""
Local development runner for Likable GitHub.
This script runs the app in local mode without Docker/nginx setup.
"""

import os

if __name__ == "__main__":
    # Ensure we're not in HF Spaces mode for local development
    if "SPACE_ID" in os.environ:
        del os.environ["SPACE_ID"]
    if "HF_SPACE" in os.environ:
        del os.environ["HF_SPACE"]

    # Run the main app
    from app import GradioUI
    from kiss_agent import KISSAgent

    agent = KISSAgent()
    print("🚀 Starting Likable GitHub in local development mode...")
    print("📱 Main app will be available at: http://localhost:7860")
    print("🔍 Preview apps will be available at: http://localhost:7861")

    GradioUI(agent).launch(share=False, server_name="0.0.0.0", server_port=7860)
