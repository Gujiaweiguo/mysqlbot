from __future__ import annotations

from sqlalchemy import update
from sqlmodel import Session, select

from apps.system.models.system_model import AiModelDetail
from common.core.db import engine

MODEL_NAME = "CI Deterministic G4 Model"
MODEL_BASE = "ci-deterministic-demo-sales"
MODEL_API_DOMAIN = "http://ci-deterministic.local"


def main() -> None:
    with Session(engine) as session:
        session.exec(update(AiModelDetail).values(default_model=False))

        model = session.exec(
            select(AiModelDetail).where(AiModelDetail.name == MODEL_NAME)
        ).first()

        if model is None:
            model = AiModelDetail.model_validate(
                {
                    "supplier": 1,
                    "name": MODEL_NAME,
                    "model_type": 1,
                    "base_model": MODEL_BASE,
                    "default_model": True,
                    "api_key": "",
                    "api_domain": MODEL_API_DOMAIN,
                    "protocol": 1,
                    "config": "[]",
                    "status": 1,
                    "create_time": 0,
                }
            )
        else:
            model.supplier = 1
            model.model_type = 1
            model.base_model = MODEL_BASE
            model.default_model = True
            model.api_key = ""
            model.api_domain = MODEL_API_DOMAIN
            model.protocol = 1
            model.config = "[]"
            model.status = 1

        session.add(model)
        session.commit()
        session.refresh(model)
        print(f"Seeded deterministic CI model: id={model.id} name={model.name}")


if __name__ == "__main__":
    main()
