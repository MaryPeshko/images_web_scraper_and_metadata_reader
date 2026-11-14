import functools
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import spider.spider as spider


PROJECT_DIR = Path(__file__).parent


def main() -> None:
    handler = functools.partial(
        SimpleHTTPRequestHandler,
        directory=str(PROJECT_DIR),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

    try:
        with tempfile.TemporaryDirectory() as output_directory:
            url = f"http://127.0.0.1:{server.server_port}/dom-example.html"
            result = spider.main(["-p", output_directory, url])

            output_path = Path(output_directory)
            downloaded_images = list(output_path.glob("dinosaur_*.png"))
            subdirectories = [path for path in output_path.iterdir() if path.is_dir()]

            assert result == 0
            assert len(downloaded_images) == 1
            assert subdirectories == []
            print("PASS: dom-example.html downloaded one image without recursion")
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join()


if __name__ == "__main__":
    main()
