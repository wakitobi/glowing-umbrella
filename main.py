#!/usr/bin/env python3
from fastapi import FastAPI
import os
app = FastAPI()
os.system("python run.py &")

@app.get("/")
async def root():
    return {"message": "Hello, FastAPI!"}


@app.get("/health")
async def health():
    return {"status": "ok"}

