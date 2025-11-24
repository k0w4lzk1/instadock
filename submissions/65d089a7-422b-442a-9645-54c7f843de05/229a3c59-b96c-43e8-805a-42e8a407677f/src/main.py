from fastapi import FastAPI

# Initialize the FastAPI app
app = FastAPI(title="InstaDock Test App")

@app.get("/")
def read_root():
    """
    Returns a success message on the root endpoint.
    """
    return {
        "status": "success",
        "message": "InstaDock Submission Pipeline is Working!",
        "service_port": 8080,
        "language": "Python/FastAPI"
    }
