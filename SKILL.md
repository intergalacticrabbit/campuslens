---
name: campus-lens
description: "Turn campus notices and circulars into structured deadlines, actionable tasks, and a searchable knowledge base using Gemma 4."
version: 1.0.0
model: gemma-4-26b-a4b-it
author: CampusLens Team (OpenLake × MLH Build with Gemma 4)
tags:
  - campus
  - gemma-4
  - document-understanding
  - task-management
  - student-productivity
---

# CampusLens Agent Skill

## Overview
CampusLens empowers students to capture notice boards, circulars, announcements, and timetables, extracting actionable information using Google's **gemma-4-26b-a4b-it** model.

## Primary Capabilities
1. **Notice Extraction**: Converts circular images and texts into standardized JSON with:
   - Notice Title & Issuing Authority
   - Event Dates & Critical Deadlines
   - Physical Venue / Online Portal Link
   - Student Eligibility Requirements
   - Explicit Action Items
2. **Actionable Task Conversion**: Translates notice action items into structured to-do items with deadlines, priority weights, and completion status.
3. **Campus Knowledge Retrieval**: Searches historic campus circulars and notifies students of impending deadlines.

## Model Configuration
- **Model**: `gemma-4-26b-a4b-it` (Google Gemma 4 - 26B instruction-tuned multimodal model)
- **Task**: Vision & Document Understanding + Tool Calling
- **Safety**: Direct deterministic Python execution for database storage and task management; LLM for extraction and query understanding.

## Tool Definitions

### `search_campus_notices(keyword: str) -> str`
Search stored campus circulars and announcements by keyword, topic, venue, or category.

### `get_pending_deadlines(limit: int = 5) -> str`
Returns sorted list of upcoming campus deadlines and pending student tasks.

### `add_campus_task(title: str, deadline: str, priority: str) -> str`
Creates an actionable task or reminder tied to a campus circular.

### `complete_campus_task(task_id: str) -> str`
Marks a student task as complete.

## Prompt Guidelines for Gemma 4
Always request structured JSON output matching the following schema:
```json
{
  "title": "Clear string title",
  "category": "Academic | Examination | Hostel | Placement | Event",
  "issuer": "Issuing department/office",
  "issue_date": "YYYY-MM-DD",
  "deadline": "YYYY-MM-DD",
  "venue": "Location or Portal",
  "eligibility": "Target audience",
  "summary": "Brief 2-3 sentence overview",
  "action_items": ["Action 1", "Action 2"]
}
```
