import logging
import argparse
from gcodezaa.process import process_gcode


def main():
    parser = argparse.ArgumentParser(
        description="Postprocess G-code to add z layer anti-aliasing."
    )
    parser.add_argument("input_gcode", type=str, help="Path to the input G-code file")
    parser.add_argument("-m", "--models", type=str, help="Path to the models directory")
    parser.add_argument("-o", "--output", type=str, required=False)
    parser.add_argument("-p", "--position", type=str, required=False)
    parser.add_argument("-n", "--name", type=str, required=False)
    args = parser.parse_args()

    with open(args.input_gcode, "r", encoding="utf-8") as f:
        if args.position is not None and args.name is not None:
            x, y = args.position.split(",", maxsplit=1)
            plate_model = (args.name, float(x), float(y))
        else:
            plate_model = None
        result = process_gcode(f.readlines(), args.models, plate_model)
    with open(args.output or args.input_gcode, "w", encoding="utf-8") as f:
        f.writelines(result)
    logging.info("Success")


if __name__ == "__main__":
    main()
