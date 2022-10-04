import networkx as nx
import matplotlib.pyplot as plt

def draw_labeled_net(G: nx.DiGraph):
    plt.figure(figsize = (8,8))
    pos = nx.spring_layout(G)
    nx.draw_networkx_nodes(G, pos, node_color = get_node_colors(G), node_size = 15000)
    nx.draw_networkx_labels(G, pos, labels = get_node_labels(G), font_size = 12)
    nx.draw_networkx_edges(G, pos, edge_color = 'tab:red')
    nx.draw_networkx_edge_labels(G, pos, edge_labels = get_edge_labels(G))
    
    #adjust so that nodes don't get cut off at the edges
    plt.axis('off')
    axis = plt.gca()
    axis.set_xlim([1.2*x for x in axis.get_xlim()])
    axis.set_ylim([1.2*y for y in axis.get_ylim()])
    plt.tight_layout()
    
    plt.show()
                           
def get_node_labels(G: nx.DiGraph):
    labels = {}
    for i in range(len(G.nodes)):
        node_name = list(G.nodes)[i]
        try:
            labels[node_name] = f"{node_name}: \n{G.nodes[node_name]['data']['label']}"
        except KeyError as e:
            labels[node_name] = 'None'
    return labels
            
def get_edge_labels(G: nx.DiGraph):
    edge_labels = {}
    for edge in list(G.edges):
        try:
            edge_labels[edge] = G.get_edge_data(*edge)['label']
        except KeyError as e:
            edge_labels[edge] = 'None'
    return edge_labels
            
def get_node_colors(G: nx.DiGraph):
    colors = []
    for i in range(len(G.nodes)):
        node_name = list(G.nodes)[i]
        try:
            colors.append(f"tab:{G.nodes[node_name]['data']['color']}")
        except KeyError as e:
            colors.append('tab:red')
    return colors 