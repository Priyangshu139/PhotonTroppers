from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import io

router = APIRouter()

@router.get("/{factory_medicine}")
def get_shell(factory_medicine: str):
    # The shell script content
    script_content = f"""#!/bin/bash
# Create a Python file that prints the script name

# Get the base name of this script (without extension)
script_name=$(basename "$0" .sh)

# Step 1: Create the Python file
echo "print('$script_name')" > hi.py

# Step 2: Run the Python file
python3 hi.py
"""

    # Create in-memory file-like object
    file_like = io.BytesIO(script_content.encode("utf-8"))

    # Return as downloadable response
    return StreamingResponse(
        file_like,
        media_type="application/x-sh",
        headers={"Content-Disposition": f"attachment; filename={factory_medicine}.sh"}
    )
