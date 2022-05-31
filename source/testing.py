import numpy

inc = list(range(7,31))
seed = list(range(6,22))
plate = list(range(3,22))

for i in inc:
    for s in seed:
        for p in plate:
            print(f"{i} {s} {p}\n")