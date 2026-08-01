import os

LABEL_DIR = "labels"

for file in os.listdir(LABEL_DIR):
    if not file.endswith(".txt"):
        continue

    path = os.path.join(LABEL_DIR, file)
    new_lines = []

    with open(path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 5:
                continue
            # FORCE class to 0
            parts[0] = "0"
            new_lines.append(" ".join(parts))

    with open(path, "w") as f:
        f.write("\n".join(new_lines))
