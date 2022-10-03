#module specific imports:
import networkx as nx
from .nx_ext import draw_labeled_net
import neo4j

#------------end imports---------------------------------------------

class NeoGraph(nx.DiGraph):
    '''
    Extended directional graph class from networkx, with added functionality for storing 
    into neo4j database, initializing from neo4j database.
    '''
    def __init__(self, uri: str, user: str, password: str, incoming_graph_data=None, **attr): 
        '''
        Same as nx function declaration but also requires DB driver.
        
        [self.driver] is to be a neo4j.GraphDatabase.driver to connect to the DB
            Form: GraphDatabase.driver(uri=uri,auth=(user,password))
            
        Therefore, init requires 3 additional positional args: uri, user, password
        '''
        self.driver = neo4j.GraphDatabase.driver(uri=uri, auth = (user, password))
        nx.DiGraph.__init__(self, incoming_graph_data, **attr) #pass the rest to DiGraph's init
        
    def close(self):
        '''
        Close out the DBMS connection.
        '''
        self.driver.close()
        
    def reopen(self):
        '''
        Reopen the DBMS connection if it is closed.
        '''
        self.driver = neo4j.GraphDatabase.driver(uri=uri, auth = (user, password))
        
    def __del__(self):
        close()
    
    def store_in_neo(self):
        '''
        Add all nodes/edges in the current DiGraph to the neo4j connected DBMS.

        Ignores identical nodes/edges that are already stored in the DBMS.
        '''
        with self.driver.session() as session:
            session.execute_write(self.add_new_nodes)
            session.execute_write(self.add_new_edges)
            
    def load_from_neo(self):
        '''
        Loads all nodes/edges from a connected neo4j DBMS into a networkx graph.
        '''
        
        query = (
            f"MATCH (n)]n"
            f"RETURN n"
        )
    
        with self.driver.session() as session:
            session.execute_read(query)
    
    #---helpers for store_in_neo-----------------------------------------------------
    def add_new_nodes(self):
        for i in range(len(self.nodes)):
            node_name = list(self.nodes)[i]
            node_label = self.nodes[node_name]['data']['label']
            
            #prevent cypher injection
            node_label, node_name = sanitize(node_label, node_name)

            query = (
                f"MERGE (n:`{node_label}` \{name: `{node_name}` \}\n"
                f"ON CREATE\n"
                f"    SET n.created = timestamp()\n"
                "RETURN n, n.created"
            )
                
    def add_new_edges(self):
        for edge in self.edges:
            from_node_name = edge[0]
            from_node_label = self.nodes[from_node_name]['data']['label']
            to_node_name = edge[1]
            to_node_label = self.nodes[to_node_name]['data']['label']
            edge_label = self.edges[edge]['label']
            
            from_node_name, from_node_label, to_node_name, to_node_label, edge_label \
                = sanitize(from_node_name, from_node_label, to_node_name, to_node_label, edge_label)
            
            #match edge based on from_node--edge_label-->to_node
            #do not allow duplicate edges in parallel of the same type
            query = (
                f"MERGE (n:{from_node_label} \{name: {from_node_name} \})"
                f"-[e:{edge_label}]->(n2:{to_node_label} \{name: {to_node_name} \})\n"
                f"ON CREATE\n"
                f"    SET e.created = timestamp()\n"
                "RETURN e"
            )
#-------end helpers for store_in_neo--------------------------------------


#------------non-class helper functions-----------------------------------                
def sanitize(*strings):
    '''
    Removes backticks and semicolons from a string to prevent early termination or exit 
    from a cypher escape block.
    '''
    sanitized = []
    
    for string in strings:
        #prevent use of any nonchars to prevent cypher injection
        sanitized.append(string.replace('`', '').replace(';', '') \
                .replace(' ','').replace('/','').replace ('(','') \
                .replace(')','').replace('{','') \
                .replace('}',''))
    return tuple(sanitized)
                         
                        
                         
                         