from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database import get_db, init_db, TodoModel, UserModel
from auth import (
    get_current_active_user,
    authenticate_user,
    create_access_token,
    get_password_hash,
    Token,
    User,
    UserCreate,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="TODO CRUD API", version="2.0.0")

# Initialize database on startup
@app.on_event("startup")
def on_startup():
    init_db()

# Data Models
class TodoBase(BaseModel):
    title: str
    description: str = None
    completed: bool = False

class Todo(TodoBase):
    id: int
    created_at: str

# In-memory storage (replaced by database)
# todos_db = {}
# next_id = 1

# ==================== AUTH ENDPOINTS ====================
@app.post("/register", response_model=User)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if username exists
    db_user = db.query(UserModel).filter(UserModel.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Check if email exists
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    new_user = UserModel(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
def read_users_me(current_user: UserModel = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

# ==================== CREATE ====================
@app.post("/todos", response_model=Todo)
def create_todo(
    todo: TodoBase,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Create a new TODO item (requires authentication)"""
    new_todo = TodoModel(
        title=todo.title,
        description=todo.description,
        completed=todo.completed,
        user_id=current_user.id
    )
    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)
    return new_todo

# ==================== READ ====================
@app.get("/todos", response_model=List[Todo])
def get_all_todos(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get all TODO items for the current user (requires authentication)"""
    todos = db.query(TodoModel).filter(TodoModel.user_id == current_user.id).all()
    return todos

@app.get("/todos/{todo_id}", response_model=Todo)
def get_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get a specific TODO item by ID (requires authentication)"""
    todo = db.query(TodoModel).filter(
        TodoModel.id == todo_id,
        TodoModel.user_id == current_user.id
    ).first()
    if not todo:
        raise HTTPException(status_code=404, detail="TODO not found")
    return todo

# ==================== UPDATE ====================
@app.put("/todos/{todo_id}", response_model=Todo)
def update_todo(
    todo_id: int,
    todo_update: TodoBase,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Update a TODO item (requires authentication)"""
    todo = db.query(TodoModel).filter(
        TodoModel.id == todo_id,
        TodoModel.user_id == current_user.id
    ).first()
    if not todo:
        raise HTTPException(status_code=404, detail="TODO not found")
    
    todo.title = todo_update.title
    todo.description = todo_update.description
    todo.completed = todo_update.completed
    
    db.commit()
    db.refresh(todo)
    return todo

@app.patch("/todos/{todo_id}", response_model=Todo)
def toggle_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Toggle TODO completion status (requires authentication)"""
    todo = db.query(TodoModel).filter(
        TodoModel.id == todo_id,
        TodoModel.user_id == current_user.id
    ).first()
    if not todo:
        raise HTTPException(status_code=404, detail="TODO not found")
    
    todo.completed = not todo.completed
    db.commit()
    db.refresh(todo)
    return todo

# ==================== DELETE ====================
@app.delete("/todos/{todo_id}")
def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Delete a TODO item (requires authentication)"""
    todo = db.query(TodoModel).filter(
        TodoModel.id == todo_id,
        TodoModel.user_id == current_user.id
    ).first()
    if not todo:
        raise HTTPException(status_code=404, detail="TODO not found")
    
    db.delete(todo)
    db.commit()
    return {"message": "TODO deleted successfully", "deleted_todo": todo}

# ==================== UTILITY ====================
@app.get("/")
def root():
    """Root endpoint with API info"""
    return {
        "message": "Welcome to TODO CRUD API v2.0 with Authentication",
        "endpoints": {
            "register": "POST /register",
            "login": "POST /token",
            "current_user": "GET /users/me",
            "create": "POST /todos",
            "read_all": "GET /todos",
            "read_one": "GET /todos/{todo_id}",
            "update": "PUT /todos/{todo_id}",
            "toggle": "PATCH /todos/{todo_id}",
            "delete": "DELETE /todos/{todo_id}",
            "clear_all": "DELETE /todos",
            "docs": "/docs"
        },
        "note": "Most endpoints require authentication. Use /token to login and get access token."
    }

@app.delete("/todos")
def clear_all_todos(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """Clear all TODO items for the current user (requires authentication)"""
    db.query(TodoModel).filter(TodoModel.user_id == current_user.id).delete()
    db.commit()
    return {"message": "All TODOs cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
