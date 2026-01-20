from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime

app = FastAPI(title="TODO CRUD API", version="1.0.0")

# Data Models
class TodoBase(BaseModel):
    title: str
    description: str = None
    completed: bool = False

class Todo(TodoBase):
    id: int
    created_at: str

# In-memory storage
todos_db = {}
next_id = 1

# ==================== CREATE ====================
@app.post("/todos", response_model=Todo)
def create_todo(todo: TodoBase):
    """Create a new TODO item"""
    global next_id
    new_todo = {
        "id": next_id,
        "title": todo.title,
        "description": todo.description,
        "completed": todo.completed,
        "created_at": datetime.now().isoformat()
    }
    todos_db[next_id] = new_todo
    next_id += 1
    return new_todo

# ==================== READ ====================
@app.get("/todos", response_model=List[Todo])
def get_all_todos():
    """Get all TODO items"""
    return list(todos_db.values())

@app.get("/todos/{todo_id}", response_model=Todo)
def get_todo(todo_id: int):
    """Get a specific TODO item by ID"""
    if todo_id not in todos_db:
        raise HTTPException(status_code=404, detail="TODO not found")
    return todos_db[todo_id]

# ==================== UPDATE ====================
@app.put("/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: int, todo_update: TodoBase):
    """Update a TODO item"""
    if todo_id not in todos_db:
        raise HTTPException(status_code=404, detail="TODO not found")
    
    todos_db[todo_id]["title"] = todo_update.title
    todos_db[todo_id]["description"] = todo_update.description
    todos_db[todo_id]["completed"] = todo_update.completed
    
    return todos_db[todo_id]

@app.patch("/todos/{todo_id}", response_model=Todo)
def toggle_todo(todo_id: int):
    """Toggle TODO completion status"""
    if todo_id not in todos_db:
        raise HTTPException(status_code=404, detail="TODO not found")
    
    todos_db[todo_id]["completed"] = not todos_db[todo_id]["completed"]
    return todos_db[todo_id]

# ==================== DELETE ====================
@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    """Delete a TODO item"""
    if todo_id not in todos_db:
        raise HTTPException(status_code=404, detail="TODO not found")
    
    deleted_todo = todos_db.pop(todo_id)
    return {"message": "TODO deleted successfully", "deleted_todo": deleted_todo}

# ==================== UTILITY ====================
@app.get("/")
def root():
    """Root endpoint with API info"""
    return {
        "message": "Welcome to TODO CRUD API",
        "endpoints": {
            "create": "POST /todos",
            "read_all": "GET /todos",
            "read_one": "GET /todos/{todo_id}",
            "update": "PUT /todos/{todo_id}",
            "toggle": "PATCH /todos/{todo_id}",
            "delete": "DELETE /todos/{todo_id}",
            "docs": "/docs"
        }
    }

@app.delete("/todos")
def clear_all_todos():
    """Clear all TODO items"""
    global todos_db
    todos_db.clear()
    return {"message": "All TODOs cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
