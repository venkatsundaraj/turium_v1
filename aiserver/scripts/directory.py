from pathlib import Path
import json
from fastapi import HTTPException

OUTPUT_DIR = Path('verification')


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    file = OUTPUT_DIR / 'hello.json'
    raise HTTPException (
        status_code=401,
        detail="Somethig went wrong"
    )
    # file.write_text(json.dumps({"hello":"world"}),  encoding="utf-8")
    # print("Hello from ai-server!")


if __name__ == "__main__":
    main()
