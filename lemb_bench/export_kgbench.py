import argparse
import csv
from pathlib import Path

from kgbench import load


def label(mapping, index: int) -> str:
    """Return the textual identifier stored at an integer KGBench index."""
    item = mapping[int(index)]
    if isinstance(item, (tuple, list)):
        item = item[0]
    return str(item)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a KGBench graph as a simple subject/predicate/object CSV."
    )
    parser.add_argument(
        "--dataset",
        default="dmg777k",
        help="KGBench dataset name (default: dmg777k)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="destination CSV path",
    )
    args = parser.parse_args()

    data = load(args.dataset, final=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["subject", "predicate", "object"])
        for subject, predicate, object_ in data.triples:
            writer.writerow(
                [
                    label(data.i2e, subject),
                    label(data.i2r, predicate),
                    label(data.i2e, object_),
                ]
            )

    print(f"Saved {len(data.triples)} triples to {args.output}")


if __name__ == "__main__":
    main()
