import src.config as config
from src.orchestrator import ETLPipeline

if __name__ == "__main__":
    pipeline = ETLPipeline(config)
    pipeline.run_full_pipeline()
    #pipeline.run_extract() # Run extract again to test state management