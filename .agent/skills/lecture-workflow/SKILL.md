---
name: Lecture Study Workflow
description: A comprehensive step-by-step workflow guide for studying each lecture, from pre-study setup through documentation and reflection.
---

# Lecture Study Workflow Guide

## 🔄 Step-by-Step Workflow for Each Lecture

Follow this workflow for every lecture in your backend course:

---

## Phase 1: Pre-Study (5-10 minutes)

### 1. Set Up Your Environment
```bash
# Create a new directory for this lecture
mkdir lecture_[NUMBER]_[topic_name]
cd lecture_[NUMBER]_[topic_name]

# Create virtual environment if needed
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Create main files
touch main.py
touch notes.md
touch exercises.py
```

### 2. Review Context
- [ ] Open backend_learning_tracker.md
- [ ] Check which lecture you're on
- [ ] Review what you learned in previous lectures

---

## Phase 2: Watch & Learn (30-60 minutes)

### 3. Active Watching
While watching the YouTube lecture:
- [ ] Take notes in your NotebookLM (you've already done this!)
- [ ] Pause and code along
- [ ] Mark timestamps for important concepts
- [ ] List questions that arise

### 4. Query NotebookLM for Lecture Notes
**In Claude Desktop App (where NotebookLM MCP is connected):**
```
Query: "Show me notes for Lecture [NUMBER]"
Query: "What are the key concepts from [Topic]?"
Query: "What code examples are there for [Concept]?"
```

---

## Phase 3: Map to FastAPI (15-30 minutes)

### 5. Identify Core Concepts
List the main concepts from the lecture:
```
Example for a routing lecture:
- HTTP methods (GET, POST, PUT, DELETE)
- URL path structure
- Route parameters
- Query strings
```

### 6. Find FastAPI Documentation
**Ask Claude (in this chat or desktop):**
```
"Which FastAPI documentation sections cover [concept]?"
"Show me FastAPI examples for [topic]"
```

**Browse FastAPI docs:**
- Tutorial: https://fastapi.tiangolo.com/tutorial/
- Advanced: https://fastapi.tiangolo.com/advanced/
- Reference: https://fastapi.tiangolo.com/reference/

### 7. Create Mapping Document
In your `notes.md`:
```markdown
# Lecture [X]: [Title]

## Concepts from YouTube Course
1. [Concept 1]
2. [Concept 2]

## FastAPI Documentation Mapping
- Concept 1 → [FastAPI Tutorial Section](link)
- Concept 2 → [FastAPI Tutorial Section](link)

## Key Differences/Similarities
- Course uses [framework/approach]
- FastAPI does it with [FastAPI approach]
```

---

## Phase 4: Practice Implementation (1-2 hours)

### 8. Start with FastAPI Examples
Copy the basic example from FastAPI docs:
```python
# main.py
from fastapi import FastAPI

app = FastAPI()

# Start with the simplest example
@app.get("/")
def read_root():
    return {"message": "Hello World"}
```

### 9. Implement Lecture Concepts
Gradually add features you learned:
```python
# Add what you learned from the lecture
# Example: Path parameters
@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}
```

### 10. Create Practice Exercises
In `exercises.py`, create exercises based on the lecture:
```python
"""
Exercise 1: Create an endpoint that [description]
Exercise 2: Add validation for [something]
Exercise 3: Implement [feature] using [concept]
"""

# Exercise 1 Solution
# Your code here

# Exercise 2 Solution
# Your code here
```

### 11. Test Your Code
```bash
# Run the FastAPI server
fastapi dev main.py

# Open browser to test
# http://127.0.0.1:8000/docs (Swagger UI)
# http://127.0.0.1:8000/redoc (ReDoc)
```

---

## Phase 5: Deepen Understanding (30-60 minutes)

### 12. Experiment & Break Things
- [ ] Change types and see what happens
- [ ] Try invalid inputs
- [ ] Remove validations and observe errors
- [ ] Add extra parameters

### 13. Build a Mini Project
Apply the concepts to a small real-world scenario:
```
Example for routing/CRUD:
Build a simple "Books API" with:
- GET /books - list all books
- GET /books/{id} - get specific book
- POST /books - create new book
- PUT /books/{id} - update book
- DELETE /books/{id} - delete book
```

### 14. Write Tests
```python
# test_main.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}
```

Run tests:
```bash
pytest test_main.py
```

---

## Phase 6: Documentation & Reflection (15-20 minutes)

### 15. Update Learning Tracker
In `backend_learning_tracker.md`:
```markdown
### Lecture [X]: [Title]

**Date Completed**: 2026-01-28
**Status**: 🟢 Mastered

#### Key Concepts from Lecture
- [List them]

#### Mapped FastAPI Documentation
- [Links to docs]

#### Practice Exercises Completed
- [x] Exercise 1: [Description]
- [x] Exercise 2: [Description]

#### Code Examples
[Link to your practice code]

#### Notes & Insights
- [What you learned]
- [Challenges you faced]
- [Solutions you found]
```

### 16. Reflect & Document
Answer these questions in your notes:
- What was the main takeaway?
- How does FastAPI make this easier/different?
- What would you do differently next time?
- What should you review again?

### 17. Check Mastery Criteria
Can you:
- [ ] Explain the concept without notes?
- [ ] Implement it from scratch?
- [ ] Debug common errors?
- [ ] Extend the functionality?
- [ ] Write tests for it?

If yes to all → Mark as 🟢 Mastered
If mostly yes → Mark as 🟡 In Progress
If struggling → 🔴 Need to review

---

## Phase 7: Consolidation (Optional, 15-30 minutes)

### 18. Create Summary Artifacts
Choose one or more:
- [ ] Write a blog post explaining the concept
- [ ] Create a cheat sheet
- [ ] Record a voice note explaining it
- [ ] Draw a diagram of the concept
- [ ] Add to your personal documentation

### 19. Share or Teach
- Explain it to a rubber duck 🦆
- Post in a learning community
- Help someone else with the concept

### 20. Plan Next Session
- [ ] Mark current lecture as complete
- [ ] Identify next lecture
- [ ] Estimate time needed
- [ ] Schedule your next study session

---

## 📋 Quick Checklist per Lecture

Use this checklist for every lecture:

```
Lecture [X]: [Title]
□ Watched lecture
□ Queried NotebookLM for notes
□ Mapped concepts to FastAPI docs
□ Implemented basic example
□ Created practice exercises
□ Solved all exercises
□ Built mini project
□ Wrote tests
□ Ran all tests successfully
□ Updated learning tracker
□ Checked mastery criteria
□ Marked status in tracker
□ Planned next session
```

---

## 🎯 Time Allocation Recommendation

**Total per lecture: 3-4 hours**

- Pre-Study: 10 min
- Watch & Learn: 45 min
- Map to FastAPI: 20 min
- Practice: 90 min
- Deepen: 45 min
- Document: 20 min
- Consolidation: 20 min (optional)

Adjust based on lecture complexity!

---

## 🚀 Power Tips

### Tip 1: Use Claude Effectively
```
Good prompt: "Compare how [course concept] is implemented in FastAPI vs [course framework]"
Good prompt: "Show me 3 practice exercises for FastAPI [topic]"
Good prompt: "What are common mistakes when implementing [concept]?"
```

### Tip 2: Leverage NotebookLM
**In Claude Desktop with NotebookLM MCP:**
```
"Summarize lecture [X]"
"What prerequisites are needed for lecture [Y]?"
"Compare the approach in lecture [X] vs lecture [Y]"
```

### Tip 3: Build Progressively
Don't try to master everything at once. Each lecture, add ONE new thing to your growing project.

### Tip 4: Keep a "TIL" (Today I Learned) Log
Quick notes on surprising things:
```
TIL: FastAPI automatically validates types!
TIL: async/await isn't always needed
TIL: Pydantic models are incredibly powerful
```

---

## 🔧 Troubleshooting Common Issues

### Issue: "I don't understand how X maps to FastAPI"
**Solution**: Ask Claude with specific examples from your lecture

### Issue: "The FastAPI docs are too advanced"
**Solution**: Start with Tutorial section, not Advanced

### Issue: "I'm overwhelmed with too many concepts"
**Solution**: Focus on ONE concept at a time, master it, move on

### Issue: "I can't think of practice exercises"
**Solution**: Use this template:
- Create [resource]
- Read [resource]
- Update [resource]
- Delete [resource]
- Add validation for [field]
- Handle error when [scenario]

---

## 📁 Recommended Folder Structure

```
backend-learning/
├── backend_learning_tracker.md
├── lecture_workflow.md
├── lecture_01_introduction/
│   ├── main.py
│   ├── exercises.py
│   ├── test_main.py
│   └── notes.md
├── lecture_02_routing/
│   ├── main.py
│   ├── exercises.py
│   ├── test_main.py
│   └── notes.md
├── projects/
│   ├── mini_project_1/
│   └── mini_project_2/
└── resources/
    ├── fastapi_cheatsheet.md
    └── common_patterns.md
```

---

**Ready to start? Begin with Phase 1 for your first lecture!**
