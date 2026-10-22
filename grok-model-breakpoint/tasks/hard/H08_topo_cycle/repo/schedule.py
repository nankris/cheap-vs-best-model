from graph import normalize
from topo import topo_sort, CycleError

def plan(nodes, edges):
    nodes, edges = normalize(nodes, edges)
    return topo_sort(nodes, edges)
