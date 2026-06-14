"""
AI Company Tools — Open WebUI Integration
Upload this file to Open WebUI: Settings → Tools → Add Tool
"""
import json
import os
import urllib.request
from typing import Optional

TOOLS_API = os.environ.get("TOOLS_API_URL", "http://ai-tools-api:9000")
HOST_IP   = os.environ.get("HOST_IP", "192.168.2.29")


class Tools:
    def __init__(self):
        pass

    def generate_mockups(
        self,
        name: str,
        description: str,
        requirements: str,
    ) -> str:
        """
        Generate 3 UI/UX mockup designs for a project.
        Use this AFTER agreeing on the project requirements and BEFORE creating the project.
        Returns 3 clickable links to preview the mockups.

        :param name: Project name (short, English, no spaces)
        :param description: Brief project description
        :param requirements: Comma-separated list of key screens/features
        :return: Formatted message with 3 mockup links
        """
        try:
            data = json.dumps({
                "name": name,
                "description": description,
                "requirements": requirements,
            }).encode()
            req = urllib.request.Request(
                f"{TOOLS_API}/generate-mockups",
                data=data, method="POST"
            )
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=180) as r:
                result = json.load(r)

            if not result.get("success"):
                return f"❌ Failed to generate mockups: {result.get('error')}"

            mockups = result.get("mockups", [])
            lines = [f"🎨 **Here are 3 designs for {name}:**\n"]
            icons = ["1️⃣", "2️⃣", "3️⃣"]
            for m in mockups:
                i = m.get("id", 0) - 1
                icon = icons[i] if i < len(icons) else f"{m.get('id')}."
                lines.append(f"{icon} **{m.get('style','Design')}** → [{m.get('url')}]({m.get('url')})")

            lines.append("\n👆 Open each link, then tell me **which number you prefer** to start building!")
            return "\n".join(lines)

        except Exception as e:
            return f"❌ Error generating mockups: {str(e)}"

    def create_project(
        self,
        name: str,
        description: str,
        tech_stack: str,
        screens: str,
        chosen_mockup_url: Optional[str] = None,
    ) -> str:
        """
        Create a new GitHub repository and start coding the project with OpenHands.
        Use this ONLY after the user has approved the plan and chosen a mockup design.

        :param name: Project name (short, English, no spaces, e.g. 'expense-tracker')
        :param description: Brief project description
        :param tech_stack: Technology stack (e.g. 'React + FastAPI + PostgreSQL')
        :param screens: Key screens/features to implement
        :param chosen_mockup_url: URL of the mockup the user chose (optional)
        :return: Status message with GitHub repo link
        """
        try:
            data = json.dumps({
                "name": name,
                "description": description,
                "tech_stack": tech_stack,
                "screens": screens,
                "mockup_url": chosen_mockup_url or "",
            }).encode()
            req = urllib.request.Request(
                f"{TOOLS_API}/create-and-start",
                data=data, method="POST"
            )
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=60) as r:
                result = json.load(r)

            if not result.get("success"):
                return f"❌ Failed: {result.get('error')}"

            repo = result.get("repo", {})
            return (
                f"✅ **Project created and coding started!**\n\n"
                f"📁 **GitHub Repo:** {repo.get('html_url','')}\n"
                f"🤖 **OpenHands** is now writing the code...\n"
                f"⏱️ This usually takes 10–20 minutes.\n\n"
                f"You'll get a Pull Request on GitHub when it's ready for review!"
            )
        except Exception as e:
            return f"❌ Error creating project: {str(e)}"
