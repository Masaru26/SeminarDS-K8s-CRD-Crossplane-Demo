from fastapi import FastAPI, HTTPException
from datetime import datetime

app = FastAPI()

elements = {
    1: {
        "id": 1,
        "name": "Element 1",
        "description": "This is the first element.",
        "created_at": datetime.now(),
        "edited_at": datetime.now()
    },
    2: {
        "id": 2,
        "name": "Element 2",
        "description": "This is the second element.",
        "created_at": datetime.now(),
        "edited_at": datetime.now()
    },
    3: {
        "id": 3,
        "name": "Element 3",
        "description": "This is the third element.",
        "created_at": datetime.now(),
        "edited_at": datetime.now()
    }
}


@app.get("/elements")
async def get_elements():
    return elements

@app.get("/elements/{element_id}")
async def get_element(element_id: int):
    if element_id in elements:
        return elements[element_id]
    raise HTTPException(status_code=404, detail="Element not found")

@app.post("/elements")
async def create_element(element: dict):
    new_id = max((e["id"] for e in elements.values()), default=0) + 1
    element["id"] = new_id
    element["created_at"] = datetime.now()
    element["edited_at"] = datetime.now()
    elements[new_id] = element
    return element

@app.put("/elements/{element_id}")
async def update_element(element_id: int, updated_element: dict):
    if element_id in elements:
        element = elements[element_id]
        element.update(updated_element)
        element["edited_at"] = datetime.now()
        return element
    raise HTTPException(status_code=404, detail="Element not found")

@app.delete("/elements/{element_id}")
async def delete_element(element_id: int):
    if element_id in elements:
        del elements[element_id]
        return {"detail": "Element deleted"}
    raise HTTPException(status_code=404, detail="Element not found")
