from app.database import Base, engine
from app import models  # noqa: F401


def main() -> None:
    if engine is None:
        raise RuntimeError("PAYMENT_DATABASE_URL must be configured")
    Base.metadata.create_all(engine)
    print("Payment Service tables are ready.")


if __name__ == "__main__":
    main()
