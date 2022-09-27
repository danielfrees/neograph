import networkx as nx

class NeoGraph(nx.DiGraph):
    def __init__(self, driver, incoming_graph_data=None, **attr): 
        '''
        Same as nx function declaration but also requires DB driver.
        
        [driver] is expected to be a neo4j.GraphDatabase.driver to connect to the DB
            Form: GraphDatabase.driver(uri=uri,auth=(user,password))
        '''
        self.driver = driver
        nx.DiGraph.__init__(incoming_graph_data, attr) #pass the rest to DiGraph's init
    
    