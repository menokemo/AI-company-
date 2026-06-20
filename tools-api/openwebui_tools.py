"""
AI Company Tools — Open WebUI Integration
Upload this file to Open WebUI: Settings → Tools → Add Tool
"""
import json
import os
import urllib.request
from typing import Optional

TOOLS_API = os.environ.get("TOOLS_API_URL", "http://ai-tools-api:9000")
HOST_IP   = os.environ.get("HOST_IP", "localhost")


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
        :param description: A SPECIFIC, detailed description of the exact
            business/domain (what is sold or done, who the customers are,
            what makes it distinct) — not a generic one-liner. The designer
            uses ONLY this text to decide what realistic content to put in
            the mockups, so vague descriptions produce generic, irrelevant
            designs. Write 2-4 sentences capturing the real business context
            discussed with the client (e.g. instead of "an online store",
            write "an eyewear store selling prescription glasses and
            sunglasses, browsing by frame style/brand, no online payment —
            customers order via a WhatsApp button on each product").
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
            # نبني وصف مهمة كامل ومفصّل لـ OpenHands بدل إرسال حقول منفصلة
            # غير مفهومة من الـ endpoint (كان السبب في "task" فاضية تماماً)
            task = (
                f"Build a project called '{name}': {description}\n\n"
                f"Tech stack: {tech_stack}\n\n"
                f"Screens/features to implement:\n{screens}\n"
            )
            if chosen_mockup_url:
                task += f"\nDesign reference (chosen mockup): {chosen_mockup_url}\n"

            data = json.dumps({
                "name": name,
                "description": description,
                "task": task,
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

            repo_url = result.get("repo_url", "")
            coding = result.get("coding", {})
            if not coding.get("success", True):
                return (
                    f"⚠️ **Repo created but OpenHands failed to start:**\n"
                    f"📁 **GitHub Repo:** {repo_url}\n"
                    f"❌ {coding.get('error', 'Unknown error')}"
                )

            return (
                f"✅ **Project created and coding started!**\n\n"
                f"📁 **GitHub Repo:** {repo_url}\n"
                f"🤖 **OpenHands** is now writing the code...\n"
                f"⏱️ This usually takes 10–20 minutes.\n\n"
                f"You'll get a Pull Request on GitHub when it's ready for review!"
            )
        except Exception as e:
            return f"❌ Error creating project: {str(e)}"

    def check_project_status(
        self,
        name: str,
    ) -> str:
        """
        Check the REAL current status of a previously-created project by
        checking GitHub directly (commits and open Pull Requests).
        Use this whenever the user asks if a project is done, finished, or
        ready — you have NO memory of OpenHands' internal progress, so you
        MUST call this tool to get a real answer. NEVER guess or say you
        don't have the ability to check — this tool gives you the real status.

        :param name: The project name used when it was created
        :return: Real status (still in progress / completed) with details
        """
        try:
            data = json.dumps({"name": name}).encode()
            req = urllib.request.Request(
                f"{TOOLS_API}/project-status",
                data=data, method="POST"
            )
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=20) as r:
                result = json.load(r)

            if result.get("error"):
                return f"❌ {result['error']}"

            repo_url = result.get("repo_url", "")
            if result.get("still_initializing"):
                return (
                    f"⏳ **Still in progress** — OpenHands hasn't pushed any real "
                    f"code yet (only the initial empty commit exists so far).\n"
                    f"📁 Repo: {repo_url}\n"
                    f"This can take 10–20 minutes. Try checking again in a few minutes."
                )

            commits_list = "\n".join(f"- {c}" for c in result.get("recent_commits", []))
            prs = result.get("open_pull_requests", [])
            pr_text = ""
            if prs:
                pr_text = "\n\n📬 **Open Pull Request(s):**\n" + "\n".join(
                    f"- [{p['title']}]({p['url']})" for p in prs
                )

            return (
                f"✅ **Real progress found!** ({result.get('commit_count')} commits)\n"
                f"📁 Repo: {repo_url}\n\n"
                f"**Recent commits:**\n{commits_list}"
                f"{pr_text}"
            )
        except Exception as e:
            return f"❌ Error checking project status: {str(e)}"
