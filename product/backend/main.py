from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.v2 import router as v2_router
from services.v2_features import get_v2_feature_service
from services.v2_model import get_v2_prediction_service


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def preload_services() -> None:
    get_v2_feature_service()
    get_v2_prediction_service()


app.include_router(v2_router)
