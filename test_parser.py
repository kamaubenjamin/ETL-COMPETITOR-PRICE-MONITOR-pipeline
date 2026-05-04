

from src.pipeline.multi_source_pipeline import run_multi_source_pipeline
import src.config as config

sources = {
    "jumia": {
        "url": "https://www.jumia.co.ke/electronics/",
        "selector": "article.prd"
    },
    "kilimall": {
        "url": "https://www.kilimall.co.ke/search?q=electronics&page=1&source=search|enterSearch|electronics",
        "selector": ".product-item"
    }
}


result = run_multi_source_pipeline(sources, config)

print("\n=== FINAL COMPARISON ===\n")
print(result)