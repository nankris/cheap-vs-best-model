from service import compute
from render import present
def run(payload): return present(compute(payload))
