from fastapi import FastAPI

from app.routers import maps, items, monsters, resources, characters, actions
from app.db import rm_db, init_db, Session, engine

app = FastAPI(debug=True)
app.include_router(characters.router)
app.include_router(monsters.router)
app.include_router(resources.router)
app.include_router(items.router)
app.include_router(maps.router)
app.include_router(actions.router)


@app.on_event("startup")
def on_startup():
    rm_db()
    init_db()
    with Session(engine) as session:
        pass
        characters.load_base_character(session, 5)
        print(f"loaded items: {items.load_items_data(session)}")
        print(f"loaded maps: {maps.load_maps_data(session)}")
        print(f"loaded monsters: {monsters.load_monsters_data(session)}")
        print(f"loaded resources: {resources.load_resources_data(session)}")
    pass


@app.get("/ping")
async def pong():
    return {"ping": "pong!"}





