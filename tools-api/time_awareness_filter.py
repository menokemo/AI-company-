"""
title: AI Company Time Awareness
author: AI Company
description: >
    يحقن توقيتًا حقيقيًا في كل رسالة (من العميل ومن مدير المشروع) عشان يكون
    عنده إدراك حقيقي بمرور الوقت — مثلاً يعرف إنه عدّى ١٠ دقايق من وقت ما قال
    "هبدأ البناء الآن"، فمايكررش نفس الجملة من غير وعي بالزمن.
"""
from datetime import datetime


class Filter:
    def __init__(self):
        # دايمًا مفعّل تلقائيًا — بدون اعتماد على تفعيل المستخدم اليدوي
        self.toggle = False

    def inlet(self, body: dict, __user__: dict = None) -> dict:
        """يحقن التوقيت الحالي في آخر رسالة من العميل قبل وصولها للموديل."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        messages = body.get("messages", [])
        if messages and messages[-1].get("role") == "user":
            content = messages[-1].get("content", "")
            if isinstance(content, str) and not content.startswith("["):
                messages[-1]["content"] = f"[{now}] {content}"
        return body

    def outlet(self, body: dict, __user__: dict = None) -> dict:
        """يحقن التوقيت الحالي في رد مدير المشروع قبل عرضه/حفظه."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        messages = body.get("messages", [])
        if messages and messages[-1].get("role") == "assistant":
            content = messages[-1].get("content", "")
            if isinstance(content, str) and not content.startswith("["):
                messages[-1]["content"] = f"[{now}] {content}"
        return body
