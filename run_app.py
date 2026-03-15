import asyncio
import sys

import streamlit.web.cli as stcli


def main() -> None:
    # Ensure there's an event loop available for Streamlit on Python 3.14+
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    # Delegate to Streamlit's CLI entrypoint
    sys.argv = ["streamlit", "run", "vocab_trainer_app.py"]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()

