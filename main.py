import datetime
from contextlib import asynccontextmanager
from typing import Annotated, AsyncGenerator

import uvicorn
from fastapi import FastAPI, Query, Depends, HTTPException
from sqlalchemy import create_engine, select, desc
from sqlalchemy.orm import Session
from sqlmodel import SQLModel, Field
from starlette.middleware.cors import CORSMiddleware

class Board(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    content: str
    createdDate: datetime.datetime = Field(default_factory=datetime.datetime.now, nullable=False)

class BoardRead(SQLModel):
    id: int
    title: str
    content: str
    createdDate: datetime.datetime

class BoardUpdate(SQLModel):
    title: str | None = None
    content: str | None = None

postgres_url = "postgresql://postgres:1234@localhost/cloudnative"
engine = create_engine(postgres_url)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    create_db_and_tables()
    print("Database tables created on startup!")
    yield
    print("Application shutting down")

app = FastAPI(
      title="Cloud Native Backend",
      description="API doc",
      version="1.0.0",
      lifespan=lifespan
      )

origins = [
    "http://localhost",
    "http://localhost:5500",
    "http://localhost:3000",
    "http://127.0.0.1:5500",
    ]

app.add_middleware(
      CORSMiddleware,
      allow_origins=origins,
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
      )

@app.post("/boards")
def create_board(board: Board, session: SessionDep):
    session.add(board)
    session.commit()
    session.refresh(board)
    return {"ok": True}

@app.get("/boards", response_model=list[BoardRead])
def get_all_boards(
      session: SessionDep,
      limit: Annotated[int, Query(ge=1, le=10)] = 10,
      offset: Annotated[int, Query(ge=0)] = 0):
    statement = select(Board).order_by(desc(Board.createdDate)).offset(offset).limit(limit)
    boards = session.scalars(statement).all()
    return boards

@app.get("/boards/{board_id}", response_model=BoardRead)
def get_board(board_id: int, session: SessionDep):
    board = session.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board

@app.put("/boards/{board_id}", response_model=BoardRead)
def update_board(
      board_id: int,
      board_update: BoardUpdate,
      session: SessionDep
      ):
    board = session.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    update_data = board_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(board, key, value)

    session.add(board)
    session.commit()
    session.refresh(board)

    return board

@app.delete("/boards/{board_id}")
def delete_board(board_id: int, session: SessionDep):
    board = session.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    session.delete(board)
    session.commit()

    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
