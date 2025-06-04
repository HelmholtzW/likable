#!/usr/bin/env python3
"""
Test script demonstrating GradioManagerAgent with Gradio UI integration.

This script shows how to use the GradioManagerAgent with the GradioUI
to create a web interface for the multi-agent development workflow.
"""

import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from manager_agent import GradioManagerAgent
    from smolagents.gradio_ui import GradioUI

    def main():
        """Main function to launch the Gradio UI with the GradioManagerAgent."""
        print("🚀 Initializing GradioManagerAgent...")

        # Create the manager agent
        manager_agent = GradioManagerAgent()

        print(f"✅ Manager agent created successfully!")
        print(f"   - Name: {manager_agent.name}")
        print(f"   - Description: {manager_agent.description[:100]}...")
        print(f"   - Is CodeAgent: {hasattr(manager_agent, 'run')}")

        # Create the Gradio UI
        print("\n🎨 Creating Gradio UI...")
        gradio_ui = GradioUI(agent=manager_agent)

        print("✅ Gradio UI created successfully!")
        print("\n🌐 Launching Gradio interface...")
        print("   - The interface will be available at the URL shown below")
        print("   - You can now interact with the multi-agent development workflow")
        print("   - Try asking: 'Create a simple calculator app'")

        # Launch the Gradio interface
        # Note: Set share=False for local development, share=True to create a public link
        gradio_ui.launch(share=False, server_name="0.0.0.0", server_port=7860)

    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please make sure all dependencies are installed and modules are available.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
