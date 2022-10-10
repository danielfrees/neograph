'''
nx_to_neo scripts extend the networkx DiGraph class to a derived NeoGraph class with methods for interacting with neo4j.

Interactions with neo4j are currently achieved using sanitized Cypher queries through the neo4j driver.

TODO:
    -Fix driver close functionality
    -Change network plot to use pyvis, networkx does not work well for larger plots
    -Batch add node and edge queries for better performance.
    -Add drop constraint functionality
    -Add graph deletion functionality (requiring confirmation)

POSSIBLE TODO:
    -Use apoc to make queries better.

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
        if self.driver:
            self.driver.close()
        
    def reopen(self):
        '''
        Reopen the DBMS connection if it is closed.
        '''
        self.driver = neo4j.GraphDatabase.driver(uri=uri, auth = (user, password))
        
    def __del__(self):
        if self.driver:
            self.close()
        super().__del__()
    
    def store_in_neo(self, verbose = False):
        '''
        Add all nodes/edges in the current DiGraph to the neo4j connected DBMS.

        Ignores identical nodes/edges that are already stored in the DBMS.
        
        Use [verbose] if you want feedback on transaction responses.
        '''
        with self.driver.session() as session:
            session.write_transaction(self.__add_new_nodes, verbose)
            session.write_transaction(self.__add_new_edges, verbose)
            
    def load_from_neo(self):
        '''
        UNFINISHED, currently just reads neo data.
        
        Loads all nodes/edges from a connected neo4j DBMS into a networkx graph.
        Will not load duplicate nodes or edges. 
        
        Wrapper for work function __load_from_neo.
        
        Returns None if nothing in DBMS instance.
        '''
        record = None
        
        with self.driver.session() as session:
            record = session.read_transaction(self.__load_from_neo)
            
        if record:
            print(record)
        else:
            print('Nothing found in this DBMS instance.')
        return record
    
    def __load_from_neo(self, tx):
        query = (
            f"MATCH (n)\n"
            f"RETURN n"
        )
    
        result = tx.run(query)
        record = result.data()
        return record
    
    def read_from_neo(self):
        '''
        Prints and returns the current data stored in the connected neo4j DBMS.
        
        Wrapper for work function __read_from_neo.
        
        Returns None if nothing in DBMS instance.
        '''
        record = None
        
        with self.driver.session() as session:
            record = session.read_transaction(self.__read_from_neo)
            
        if record:
            print(record)
        else:
            print('Nothing found in this DBMS instance.')
        return record
    
    def __read_from_neo(self, tx):
        query = (
            f"MATCH (n)\n"
            f"RETURN n"
        )
    
        result = tx.run(query)
        record = result.data()
        return record
        
    
    #---helpers for store_in_neo-----------------------------------------------------   
    def __add_new_nodes(self, tx, verbose = False):
        '''
        Adds all of the current nodes in the graph to connected DBMS if they do not exist.
        Nodes are matched based on label, name.
        If a node is matched but the NeoGraph has new properties, these will be added to the matched node. 
        
        Marks creation timestamp if creating a new unmatched node.
        '''
        for i in range(len(self.nodes)):
            node_name = str(list(self.nodes)[i])
            node_label = str(self.nodes[node_name]['data']['label'])
            
            #get extra attrs
            other_props = self.nodes[node_name]['data'].copy()   #extra attributes on nodes are kept under 'data' in nx
            other_props.pop('label') #label is reserved for neo4j label usage, not considered a supplement attribute
            other_props = self.__unpack_props(other_props) #handles injection protection within __unpack_props
            
            #prevent cypher injection on name/label
            node_label, node_name = sanitize(node_label, node_name)

            if verbose:
                print('Storing the following node...')
                print(f"name: {node_name}")
                print(f"label: {node_label}")
                print(f"other props: {other_props}")
                print()
            
            query = (
                f"MERGE (n: {node_label} {{name: \"{node_name}\"}})\n"
                f"ON CREATE\n"
                f"    SET n.created = timestamp()\n"
                f"SET n += {{{other_props}}}\n"
                f"RETURN n, n.created"
            )
            
            result = tx.run(query)
            record = result.data()
            
            if verbose:
                if record:
                    print("\nAdd node query result:")
                    print(record)
                else:
                    print("No node added, nor does it exist. Check query syntax or raise github issue.")
                
    def __add_new_edges(self, tx, verbose = False):
        '''
        Adds all of the current edges in the graph to connected DBMS if they do not exist.
        
        If an edge already exists with the same label (but different properties), the new properties 
        will be added to the pre-existing edge.
        
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
            
            #get extra attrs
            props = self.edges[edge].copy()  #extra attrs are maintained at highest level for edges in nx (no 'data' subcat)
            props.pop('label')  #label is required under neo4j standards, not an extra
            props = self.__unpack_props(props)
            
            from_node_name, from_node_label, to_node_name, to_node_label, edge_label \
                = sanitize(from_node_name, from_node_label, to_node_name, to_node_label, edge_label)
            
            #match edge based on from_node--edge_label-->to_node
            #do not allow duplicate edges in parallel of the same type
            query = (
                f"MERGE (n:{from_node_label} {{name: \"{from_node_name}\" }})\n"
                f"MERGE (n2:{to_node_label} {{name: \"{to_node_name}\" }})\n"
                f"MERGE (n)-[e:{edge_label}]->(n2)\n"
                f"ON CREATE\n"
                f"    SET e.created = timestamp()\n" 
                f"SET e += {{{props}}}\n"                       #add additional properties to a prior edge if it already exists
                "RETURN e"
            )
            
            result = tx.run(query)
            record = result.data()
            
            if verbose:
                if record:
                    print("\nAdd relationship query result:")
                    print(record)
                else:
                    print("No relationship added, nor does it exist. Check query syntax or raise github issue.")
            
    def __unpack_props(self, props):
        '''
        Takes in a dict of added properties to be unpacked into Cypher syntax and placed within curly bracks. 
        Begins with , because name must already exist in properties and therefore any additional properties must be preceded by a comma
        
        ie: props = {'color':'red', 'favorite_food':'pizza'} -> ",'color':'red', 'favorite_food':'pizza"
        
        If props dict is empty, returns empty string.
        
        Sanitizes properties as well.
        '''
        
        unpacked_props = ""
        for key, value in props.items():
            if isinstance(value, str):
                unpacked_props += f", {sanitize(str(key))}:\"{sanitize(value)}\""
            else:
                unpacked_props += f", {sanitize(str(key))}:\"{value}\""
        return unpacked_props[1:] #remove first comma
            
#-------end helpers for store_in_neo--------------------------------------

    def create_constraint(self, label, prop, on = 'node', constraint_type = 'unique'):
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
                                        
            
    def __create_constraint(self, tx, label, prop, on, pattern, requirement):
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
                f"CREATE CONSTRAINT {label}_{on}_{prop}_unique IF NOT EXISTS\n"
                f"FOR {pattern}\n"
                f"REQUIRE x.{prop} {requirement}"    #note that the pattern will always be aliased as x, regardless of node vs. relationship
            )
        result = tx.run(query)
        record = result.data()
        if record:
            print("\nAdd constraint query result:")
            print(record)
        else: 
            print(f'Desired constraint on {on}s for {label}{{{prop}}} already exists.')
        
    def get_constraints(self):
        '''
        Return & print all current constraints in the DBMS linked to self.driver.
        
        Wrapper for work function __get_constraints.
        '''
        with self.driver.session() as session:
            session.read_transaction(self.__get_constraints)
         
    def __get_constraints(self, tx):
        '''
        Worker function to enact transaction for get_constraints.
        '''
        query = (
            "SHOW CONSTRAINTS"
            )
        result = tx.run(query)
        record = result.data()
        if record:
            print("\nGet constraint query result:")
            print(record)
        else:
            print('No constraints found. Use create_constraint to set constraints from a NeoGraph.')
        return result

#------------non-class helper functions-----------------------------------                
def sanitize(*strings : str):
    '''
    Removes backticks and semicolons from a string to prevent early termination or exit 
    from a cypher escape block.
    
    Then appends backticks on either end to allow for use of spaces and hyphen.
    
    Note: input MUST be strings
    '''
    sanitized = []
    
    for string in strings:
        #prevent use of any nonchars to prevent cypher injection
        string = string.replace('`', '').replace(';', '') \
                .replace('/','').replace ('(','') \
                .replace(')','').replace('{','') \
                .replace('}','')
        
        sanitized.append(string)
    
    if len(sanitized) == 1:
        return sanitized[0]
    else:
        return tuple(sanitized)
    
    
    
                         
                        
                         
                         