import networkx as nx
from app.models.transaction import Transaction


def build_graph(transactions: list) -> nx.MultiDiGraph:
    """
    Build transaction graph from transactions.

    Uses MultiDiGraph so multiple transactions between
    the same sender and receiver are preserved.
    """

    G = nx.MultiDiGraph()

    nodes = {}

    for t in transactions:

        u = t.sender_account
        v = t.receiver_account
        amt = float(t.amount or 0)
        t_date = t.date

        # Skip incomplete transactions
        if not u or not v:
            continue

        # Initialize sender node
        if u not in nodes:
            nodes[u] = {
                "total_received": 0.0,
                "total_sent": 0.0,
                "transaction_count": 0,
                "first_seen": t_date,
                "last_seen": t_date,
                "risk_score": 0.0
            }

        # Initialize receiver node
        if v not in nodes:
            nodes[v] = {
                "total_received": 0.0,
                "total_sent": 0.0,
                "transaction_count": 0,
                "first_seen": t_date,
                "last_seen": t_date,
                "risk_score": 0.0
            }

        # Sender stats
        nodes[u]["total_sent"] += amt
        nodes[u]["transaction_count"] += 1

        if t_date:
            if nodes[u]["first_seen"] is None or t_date < nodes[u]["first_seen"]:
                nodes[u]["first_seen"] = t_date

            if nodes[u]["last_seen"] is None or t_date > nodes[u]["last_seen"]:
                nodes[u]["last_seen"] = t_date

        # Receiver stats
        nodes[v]["total_received"] += amt
        nodes[v]["transaction_count"] += 1

        if t_date:
            if nodes[v]["first_seen"] is None or t_date < nodes[v]["first_seen"]:
                nodes[v]["first_seen"] = t_date

            if nodes[v]["last_seen"] is None or t_date > nodes[v]["last_seen"]:
                nodes[v]["last_seen"] = t_date

        # Suspicious transaction flag
        is_suspicious = amt >= 500000

        # MultiDiGraph preserves multiple transactions
        G.add_edge(
            u,
            v,
            txn_id=t.id,
            amount=amt,
            weight=amt,
            date=str(t_date) if t_date else None,
            description=t.description,
            type=t.type,
            is_suspicious=is_suspicious
        )

    # Add node attributes
    for node_id, attrs in nodes.items():

        if attrs["first_seen"]:
            attrs["first_seen"] = str(attrs["first_seen"])

        if attrs["last_seen"]:
            attrs["last_seen"] = str(attrs["last_seen"])

        G.add_node(node_id, **attrs)

    return G


def build_multi_statement_graph(case_id: str) -> nx.MultiDiGraph:
    """
    Build graph from all transactions in a case.
    """
    transactions = Transaction.query.filter_by(
        case_id=case_id,
        is_failed=False
    ).all()

    return build_graph(transactions)


def graph_to_json(G):
    """
    Convert graph to JSON serializable format.
    """
    from networkx.readwrite import json_graph

    return json_graph.node_link_data(G)