"""Entry point for the MiniLSP server."""
import asyncio
import sys

from src.stdio_server import run_server


def main() -> None:
    try:
        asyncio.run(run_server())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
