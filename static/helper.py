import os

import aiofiles
import bcrypt
from fastapi import UploadFile


async def upload_file(file: UploadFile):
    base_name = os.path.splitext(file.filename)[0]

    # Обрезаем до 72 байт (не символов!)
    # .encode() -> bytes, обрезаем, потом .decode()
    truncated = base_name.encode()[:72].decode(errors="ignore")

    salt = bcrypt.gensalt()
    random_name = bcrypt.hashpw(truncated.encode(), salt).decode()

    clean_name = random_name.replace("/", "_").replace(".", "_")

    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{clean_name}{file_extension}"
    directory = "static/media"
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, filename)
    async with aiofiles.open(file_path, mode="wb") as f:
        content = await file.read()
        await f.write(content)

    return f"static/media/{filename}"
