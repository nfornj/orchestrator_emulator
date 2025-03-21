from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Orchestrator Service"
    
    # Redis settings
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PAYLOAD_TTL: int = 3600  # 1 hour
    REDIS_STATUS_TTL: int = 7200   # 2 hours
    REDIS_COMPLETED_TTL: int = 86400  # 24 hours
    
    # PostgreSQL settings
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "orchestrator"
    
    # Event Hubs settings
    EVENTHUB_CONNECTION_STRING: str = "EVENTHUB_CONNECTION_STRING=Endpoint=sb://eventhubs-emulator:9092;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;UseDevelopmentEmulator=true;Transport=Kafka"
    EVENTHUB_NAME: str = "orchestrator"
    
    # Processing settings
    REVENUE_DELAY_MIN: int = 100  # ms
    REVENUE_DELAY_MAX: int = 300  # ms
    REBATE_DELAY_MIN: int = 200   # ms
    REBATE_DELAY_MAX: int = 500   # ms
    SPECIALTY_DELAY_MIN: int = 50  # ms
    SPECIALTY_DELAY_MAX: int = 150  # ms

settings = Settings() 