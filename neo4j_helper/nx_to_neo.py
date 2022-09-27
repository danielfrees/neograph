#imported in __init__.py:
#neo4j


#module specific imports:
import networkx as nx
from nx_to_neo import draw_labeled_net

#------------end imports---------------------------------------------

class NeoGraph(nx.DiGraph):
'''Extended directional graph class from networkx, with added functionality for storing 
into neo4j database, initializing from neo4j database.
'''

    def __init__(self, uri, user, password, incoming_graph_data=None, **attr): 
        '''
        Same as nx function declaration but also requires DB driver.
        
        [self.driver] is to be a neo4j.GraphDatabase.driver to connect to the DB
            Form: GraphDatabase.driver(uri=uri,auth=(user,password))
            
        Therefore, init requires 3 additional positional args: uri, user, password
        '''
        self.driver = neo4j.GraphDatabase.driver(uri=uri, auth = (user, password))
        nx.DiGraph.__init__(incoming_graph_data, attr) #pass the rest to DiGraph's init
    
    def store_in_neo(self):
    '''
    Add all nodes/edges in the current DiGraph to the neo4j connected DBMS.
    
    Ignores identical nodes/edges that are already stored in the DBMS.
    '''
    
        with self.driver.session() as session:
            session.write_transaction(self.add_new_nodes)
            session.write_transaction(self.add_new_edges)
            
    def add_new_nodes(self):
        for node in self.nodes:
            query = (
            f"OPTIONAL MATCH (n:{node['data']['label']}  "
                
            )
    def add_new_edges(self):
        for edge in self.edges: