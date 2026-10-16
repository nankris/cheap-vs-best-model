from codec import decode
from service import compute
from render import present
def run(payload):
    return present(compute(decode(payload)))
