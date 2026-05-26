from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from agente_percepcion.camera import Camera


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnostica camaras y backends de OpenCV.")
    parser.add_argument("--indices", default="0,1,2", help="Indices a probar, separados por coma.")
    parser.add_argument(
        "--backends",
        default="directshow,msmf,any",
        help="Backends a probar: directshow, msmf, any.",
    )
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--fourcc", default="MJPG")
    parser.add_argument("--output-dir", default="capturas_diagnostico")
    parser.add_argument("--preview-seconds", type=float, default=2.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    indices = [int(item.strip()) for item in args.indices.split(",") if item.strip()]
    backends = [item.strip() for item in args.backends.split(",") if item.strip()]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for index in indices:
        for backend in backends:
            print(f"Probando index={index}, backend={backend}, fourcc={args.fourcc}...")
            try:
                with Camera(
                    index=index,
                    backend=backend,
                    width=args.width,
                    height=args.height,
                    fps=args.fps,
                    fourcc=args.fourcc,
                    read_retries=20,
                ) as camera:
                    frame = camera.read()
                    path = output_dir / f"camera_{index}_{backend}_{args.fourcc}.jpg"
                    cv2.imwrite(str(path), frame)
                    print(f"OK: captura guardada en {path}")

                    start = cv2.getTickCount()
                    frequency = cv2.getTickFrequency()
                    while (cv2.getTickCount() - start) / frequency < args.preview_seconds:
                        frame = camera.read()
                        cv2.imshow(f"check_camera index={index} backend={backend}", frame)
                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            cv2.destroyAllWindows()
                            return
                    cv2.destroyAllWindows()
            except Exception as exc:
                print(f"FALLO index={index}, backend={backend}: {exc}")


if __name__ == "__main__":
    main()
