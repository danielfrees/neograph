'''
nx_to_neo scripts extend the networkx DiGraph class to a derived NeoGraph class with methods for interacting with neo4j.

Interactions with neo4j are currently achieved using sanitized Cypher queries through the neo4j driver.

Possible future update could change interactions to use APOC. 

'''


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
        self.close()
    
    def store_in_neo(self):
        '''
        Add all nodes/edges in the current DiGraph to the neo4j connected DBMS.

        Ignores identical nodes/edges that are already stored in the DBMS.
        '''
        with self.driver.session() as session:
            session.write_transaction(self.__add_new_nodes)
            session.write_transaction(self.__add_new_edges)
            
    def load_from_neo(self):
        '''
        Loads all nodes/edges from a connected neo4j DBMS into a networkx graph.
        '''
        
        query = (
            f"MATCH (n)]n"
            f"RETURN n"
        )
    
        with self.driver.session() as session:
            session.run(query)
    
    #---helpers for store_in_neo-----------------------------------------------------   
    def __add_new_nodes(self, tx):
        '''
        Adds all of the current nodes in the graph to connected DBMS if they do not exist.
        
        Marks creation timestamp if creating a new unmatched node.
        
        tx is passed by execute_write
        
        Matching based on node name & label
        '''
        for i in range(len(self.nodes)):
            node_name = list(self.nodes)[i]
            node_label = self.nodes[node_name]['data']['label']
            
            #prevent cypher injection
            node_label, node_name = sanitize(node_label, node_name)

            query = (
                f"MERGE (n: {node_label} {{name: \"{node_name}\" }})\n"
                f"ON CREATE\n"
                f"    SET n.created = timestamp()\n"
                f"RETURN n, n.created"
            )
            
            result = tx.run(query)
            print()
            print(result.single()[0])
                
    def __add_new_edges(self, tx):
        '''
        Adds all of the current edges in the graph to connected DBMS if they do not exist.
        
        Marks creation timestamp if creating new edge.
        
        tx passed by execute_write
        
        Matching based on node1 name & label, relationship, node2 name & label (direction matters). 
        Note that new nodes will be created as well if necessary to make the pattern. But this should be
        taken care of already by __add_new_nodes if running via the store_in_neo wrapper.
        '''
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
                f"MERGE (n:{from_node_label} {{name: \"{from_node_name}\" }})"
                f"-[e:{edge_label}]->(n2:{to_node_label} {{ name: \"{to_node_name}\" }})\n"
                f"ON CREATE\n"
                f"    SET e.created = timestamp()\n"
                "RETURN e"
            )
            
            result = tx.run(query)
            print()
            print(result.single()[0])
            
#-------end helpers for store_in_neo--------------------------------------

    def create_constraint(label, prop, on = 'node', constraint_type = 'unique'):
        '''
        Create a constraint for a particular node label and property. ie. :Person{name} via label = 'Person', prop = 'name'.
        
        {on} must be either 'node' or 'relationship'. Changes whether the constraint applies to nodes or relationships.
        
        {constraint_type} is currently supported for either 'unique' (uniqueness constraint) or 'exist' (existence constraint).
        
        Wrapper for __create_constraint which makes sure inputs are sanitized, and can be used to create Cypher patterns.
        '''
        pattern = None
        requirement = None
        
        #make sure the passed label and prop are sanitized
        label, prop = sanitize(label, prop)
        
        #change pattern to either match a node or a relationship
        if on == 'node':
            pattern = f"(x:{label})"
        elif on == 'relationship':
            pattern = f"()-[x:{label}]-()"
        else:
            raise ValueError("Argument {on} must be either 'node' or 'relationship'")
            
        #change constraint type -> {requirement}
        if constraint_type == 'unique':
            requirement = "IS UNIQUE"
        elif constraint_type == 'exist':
            requirement = "IS NOT NULL"
        else:
            raise ValueError("Argument {constraint_type} must be either 'unique' or 'exist'")
            
            
        #actually run constraint transaction
        with self.driver.session() as session:
                session.write_transaction(self.__create_constraint, label, prop, on, pattern, requirement)
                                        
            
    def __create_constraint(tx, label, prop, on, pattern, requirement):
        '''
        Actually create a constraint for a particular label and property. Wrapped by create_constraint.
        
        tx- passed by write_transaction (neo4j driver API)
        label- label for constraint
        prop- property for constraint
        on- 'node' or 'edge', whichever the constraint applies to
        pattern- the match pattern produced by wrapper function create_constraint
        requirement- syntax for the constraint type
        '''            
        query = (
                f"CREATE CONSTRAINT {label}({on})_{prop}_unique IF NOT EXISTS\n"
                f"FOR {pattern}\n"
                f"REQUIRE x.{prop} {requirement}"    #note that the pattern will always be aliased as x, regardless of node vs. relationship
            )
     
    def get_constraints(tx):
    '''
    Return & print all current constraints in the DBMS linked to self.driver.
    '''
        query = (
            "SHOW CONSTRAINTS"
            )
        result = tx.run(query)
        print(result.single()[0])
        return result

#------------non-class helper functions-----------------------------------                
def sanitize(*strings):
    '''
    Removes backticks and semicolons from a string to prevent early termination or exit 
    from a cypher escape block.
    
    Then appends backticks on either end to allow for use of spaces and hyphen.
    '''
    sanitized = []
    
    for string in strings:
        #prevent use of any nonchars to prevent cypher injection
        string = string.replace('`', '').replace(';', '') \
                .replace('/','').replace ('(','') \
                .replace(')','').replace('{','') \
                .replace('}','')
        
        sanitized.append(string)
        
    return tuple(sanitized)
                         
                        
                         
                         