import base64
from pathlib import Path


PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAgMBgJ9l8XQAAAAASUVORK5CYII="
)


def main() -> None:
    output = Path("output/local/logo/test-logo.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base64.b64decode(PNG_BASE64))


if __name__ == "__main__":
    main()
