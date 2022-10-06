from distutils.core import setup

setup(name='NeoGraph',
    version='0.1',
    description='NetworkX Graph Syncing with neo4j: NeoGraphs',
    long_description=("NeoGraph class extends NetworkX DiGraphs by enabling"
    "syncing with a neo4j DBMS. For detailed usage instructions visit"
    "https://github.com/danielfrees/neograph#readme"
    ),
    author='Daniel Frees',
    author_email='danielfrees247@gmail.com',
    maintainer = "Daniel Frees",
    url='https://github.com/danielfrees/neograph',
    packages=['neograph', 'neograph.nx_ext'],
    python_requires='>=3.8',
    install_requires=[
        'networkx',
        'matplotlib',
        'numpy',
        'neo4j'
    ],
    keywords='graph, networkx, neo4j'
    )