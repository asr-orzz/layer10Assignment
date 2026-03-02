from pathlib import Path

import networkx as nx
from pyvis.network import Network
from jinja2 import Template
import importlib.resources as pkg_resources

from .config import GRAPH_HTML, DB_PATH
from .graph_store import init_db, load_claims, load_entities


COLORS = {
    "person": "#4caf50",
    "issue": "#2196f3",
    "component": "#ff9800",
    "concept": "#9c27b0",
}


def build_graph(db_path: Path = DB_PATH, output_html: Path = GRAPH_HTML):
    conn = init_db(db_path)
    entities = {e.id: e for e in load_entities(conn)}
    claims = load_claims(conn)

    G = nx.MultiDiGraph()
    for ent in entities.values():
        G.add_node(ent.id, label=ent.name, color=COLORS.get(ent.type, "#607d8b"), title=ent.type)

    for claim in claims:
        subj = entities.get(claim.subject_id)
        obj_label = claim.object
        # If object references another entity id, resolve
        target_id = obj_label if obj_label in entities else None
        if target_id:
            G.add_edge(claim.subject_id, target_id, label=claim.predicate)
        else:
            # represent literal object as pseudo node
            lit_id = f"lit-{claim.id}"
            G.add_node(lit_id, label=obj_label, color="#cfd8dc", shape="box")
            G.add_edge(claim.subject_id, lit_id, label=claim.predicate)

    net = Network(height="720px", width="100%", directed=True, notebook=False)
    # pyvis sometimes fails to locate its bundled template when executed outside notebooks
    try:
        template_text = pkg_resources.files("pyvis").joinpath("templates/template.html").read_text(encoding="utf-8")
        net.template = Template(template_text)
    except Exception:
        pass
    net.from_nx(G)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    net.show(str(output_html))
    return output_html


if __name__ == "__main__":
    out = build_graph()
    print(f"Wrote graph to {out}")
