from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Aspect AI is running on Render!"}
