import os

INPUT_DIR = "screened_with_counts"
for file in os.listdir(INPUT_DIR):
    with open(os.path.join(INPUT_DIR, file), "r") as f:
        lines = f.readlines()
    f = open(os.path.join(INPUT_DIR, file), "w")

    f.write(lines[0])

    line = lines[1]
    i = 2
    while i < len(lines):
        if lines[i].startswith("K"):
            f.write(line)
            line = lines[i]
        else:
            line = line.rstrip() + lines[i]
        i += 1

    f.write(line)