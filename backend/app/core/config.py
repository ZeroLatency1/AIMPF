from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    database_url:str='postgresql+psycopg://aimpf:aimpf@localhost:5432/aimpf'
    secret_key:str='change-me'
    algorithm_version:str='1.1.0'
    cors_origins:str='http://localhost:3000'
    model_config=SettingsConfigDict(env_file='.env',extra='ignore')
settings=Settings()
